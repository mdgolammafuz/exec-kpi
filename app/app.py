import os
import time
from datetime import date, timedelta

import pandas as pd
import numpy as np
import streamlit as st
from google.cloud import bigquery
from scipy.stats import norm, chi2  # for A/B significance

# ---- CONFIG ----
st.set_page_config(page_title="Exec KPI Dashboard", layout="wide")
PROJECT = os.getenv("GCP_PROJECT", "exec-kpi")
DATASET = os.getenv("BQ_DATASET", "execkpi_execkpi")  # matches dbt output dataset

client = bigquery.Client(project=PROJECT)

# ---- minimal observability store ----
_DIAG = []  # each entry: {"label": str, "rows": int, "ms": int}

def bq_df(sql, params=None, label="query"):
    start = time.perf_counter()
    job_config = bigquery.QueryJobConfig(query_parameters=params or [])
    df = client.query(sql, job_config=job_config).result().to_dataframe()
    ms = int((time.perf_counter() - start) * 1000)
    _DIAG.append({"label": label, "rows": len(df), "ms": ms})
    return df

# ---- SIDEBAR FILTERS ----
st.sidebar.header("Filters")
end = st.sidebar.date_input("End date", value=date.today())
start = st.sidebar.date_input("Start date", value=end - timedelta(days=30))
if start > end:
    st.sidebar.error("Start date must be before end date")

show_diag = st.sidebar.checkbox("Show diagnostics", value=False)

# ---- REVENUE ----
st.title("Executive KPIs")

rev_sql = f"""
SELECT day, revenue
FROM `{PROJECT}.{DATASET}.revenue_daily`
WHERE day BETWEEN @start AND @end
ORDER BY day
"""
rev = bq_df(
    rev_sql,
    params=[
        bigquery.ScalarQueryParameter("start", "DATE", str(start)),
        bigquery.ScalarQueryParameter("end",   "DATE", str(end)),
    ],
    label="revenue_current_window",
)

col1, col2 = st.columns([2, 3])
with col1:
    st.subheader("Revenue — Selected window")
    if not rev.empty:
        st.line_chart(rev.set_index("day")["revenue"])
    else:
        st.info("No revenue rows in this date range.")

with col2:
    # compare to previous equal-length window
    window = (end - start).days + 1
    prev_start = start - timedelta(days=window)
    prev_end = end - timedelta(days=window)

    prev_rev_df = bq_df(
        f"""
        SELECT SUM(revenue) AS revenue
        FROM `{PROJECT}.{DATASET}.revenue_daily`
        WHERE day BETWEEN @s AND @e
        """,
        [
            bigquery.ScalarQueryParameter("s", "DATE", str(prev_start)),
            bigquery.ScalarQueryParameter("e", "DATE", str(prev_end)),
        ],
        label="revenue_prev_window",
    )
    prev_rev = float(prev_rev_df["revenue"].iloc[0] or 0)
    cur_rev = float(rev["revenue"].sum() if not rev.empty else 0)
    delta = cur_rev - prev_rev
    delta_pct = (delta / prev_rev * 100) if prev_rev else np.nan

    k1, k2, k3 = st.columns(3)
    k1.metric("Revenue (current)", f"${cur_rev:,.0f}")
    k2.metric("Revenue (previous)", f"${prev_rev:,.0f}")
    k3.metric("Change", f"${delta:,.0f}", None if np.isnan(delta_pct) else f"{delta_pct:+.1f}%")

# ---- A/B METRICS ----
st.markdown("---")
st.subheader("A/B Conversion")
ab = bq_df(
    f"SELECT ab_group, users, converters, conversion_rate FROM `{PROJECT}.{DATASET}.ab_metrics`",
    label="ab_metrics",
)
if not ab.empty:
    st.dataframe(ab, width="stretch")

    # A/B significance (SRM + 2-proportion z)
    if set(["A", "B"]).issubset(set(ab["ab_group"])):
        ab_idx = ab.set_index("ab_group")

        n_c = int(ab_idx.loc["A", "users"])
        n_t = int(ab_idx.loc["B", "users"])
        x_c = int(ab_idx.loc["A", "converters"])
        x_t = int(ab_idx.loc["B", "converters"])

        p_c = x_c / n_c if n_c else float("nan")
        p_t = x_t / n_t if n_t else float("nan")
        uplift = p_t - p_c if np.isfinite(p_c) and np.isfinite(p_t) else float("nan")

        # SRM (allocation sanity check)
        total = n_c + n_t
        exp = total / 2 if total else float("nan")
        chi2_stat = ((n_c - exp) ** 2) / exp + ((n_t - exp) ** 2) / exp if np.isfinite(exp) else float("nan")
        srm_p = 1 - chi2.cdf(chi2_stat, df=1) if np.isfinite(chi2_stat) else float("nan")

        # 2-proportion z-test
        denom = (n_c + n_t)
        p_pool = (x_c + x_t) / denom if denom else float("nan")
        se = np.sqrt(p_pool * (1 - p_pool) * (1/n_c + 1/n_t)) if 0 < p_pool < 1 else float("nan")
        z = uplift / se if np.isfinite(se) and se > 0 else float("nan")
        p_val = 2 * (1 - norm.cdf(abs(z))) if np.isfinite(z) else float("nan")
        ci_low = uplift - 1.96 * se if np.isfinite(se) else float("nan")
        ci_high = uplift + 1.96 * se if np.isfinite(se) else float("nan")

        st.markdown("#### A/B Significance")
        c1, c2, c3 = st.columns(3)
        c1.metric("SRM p-value", f"{srm_p:.3f}" if np.isfinite(srm_p) else "—", help="> 0.05 ≈ allocation ok")
        c2.metric("p-value (2-prop z)", f"{p_val:.3f}" if np.isfinite(p_val) else "—", help="< 0.05 ≈ significant")
        c3.metric("95% CI (uplift)",
                  f"[{ci_low:.2%}, {ci_high:.2%}]" if np.isfinite(ci_low) and np.isfinite(ci_high) else "—")
else:
    st.info("No A/B rows available.")

# ---- RETENTION HEATMAP ----
st.markdown("---")
st.subheader("Weekly Retention (Cohort × Week)")
try:
    ret = bq_df(
        f"""
        SELECT cohort_week, week_n, retention_rate
        FROM `{PROJECT}.{DATASET}.retention_weekly`
        ORDER BY cohort_week, week_n
        """,
        label="retention_weekly",
    )
    if not ret.empty:
        ret_pivot = ret.pivot(index="cohort_week", columns="week_n", values="retention_rate").fillna(0)
        # Use gradient if matplotlib is present; otherwise plain table
        try:
            idx = pd.IndexSlice
            styler = (
                ret_pivot.style
                    .format("{:.0%}")
                    .background_gradient(axis=None, cmap="Blues", subset=idx[:, :])
            )
            st.dataframe(styler, width="stretch")
        except Exception:
            st.dataframe(ret_pivot.applymap(lambda x: f"{x:.0%}"), width="stretch")
    else:
        st.info("No retention data.")
except Exception as e:
    st.error(f"Retention query failed: {e}")

# ---- DIAGNOSTICS PANEL (toggle from sidebar) ----
if show_diag:
    st.markdown("---")
    st.subheader("Diagnostics")
    if _DIAG:
        diag_df = pd.DataFrame(_DIAG)[["label", "rows", "ms"]].sort_values("ms", ascending=False)
        st.write(f"Project: `{PROJECT}`  •  Dataset: `{DATASET}`")
        st.dataframe(diag_df, width="stretch")
    else:
        st.write("No queries executed yet.")

st.caption("Data source: BigQuery views built by dbt (ab_group, funnel_users, revenue_daily, retention_weekly, ab_metrics).")
