import os
from datetime import date, timedelta
import pandas as pd
import numpy as np
import streamlit as st
from google.cloud import bigquery

# ---- CONFIG ----
st.set_page_config(page_title="Exec KPI Dashboard", layout="wide")
PROJECT = os.getenv("GCP_PROJECT", "exec-kpi")
DATASET = os.getenv("BQ_DATASET", "execkpi_execkpi")  # matches dbt output dataset

client = bigquery.Client(project=PROJECT)

def bq_df(sql, params=None):
    job_config = bigquery.QueryJobConfig(query_parameters=params or [])
    return client.query(sql, job_config=job_config).result().to_dataframe()

# ---- SIDEBAR FILTERS ----
st.sidebar.header("Filters")
end = st.sidebar.date_input("End date", value=date.today())
start = st.sidebar.date_input("Start date", value=end - timedelta(days=30))
if start > end:
    st.sidebar.error("Start date must be before end date")

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
ab = bq_df(f"SELECT ab_group, users, converters, conversion_rate FROM `{PROJECT}.{DATASET}.ab_metrics`")
if not ab.empty:
    st.dataframe(ab, width="stretch")
    if set(["A", "B"]).issubset(set(ab["ab_group"])):
        ctr = ab.set_index("ab_group")["conversion_rate"]
        ctrl = ctr.get("A", np.nan)
        trt = ctr.get("B", np.nan)
        uplift = trt - ctrl if pd.notna(ctrl) and pd.notna(trt) else np.nan
        c1, c2, c3 = st.columns(3)
        c1.metric("Control conv.", f"{ctrl:.2%}" if pd.notna(ctrl) else "—")
        c2.metric("Treatment conv.", f"{trt:.2%}" if pd.notna(trt) else "—")
        c3.metric("Uplift", f"{uplift:+.2%}" if pd.notna(uplift) else "—")
else:
    st.info("No A/B rows available.")

# ---- RETENTION HEATMAP ----
st.markdown("---")
st.subheader("Weekly Retention (Cohort × Week)")
try:
    ret = bq_df(f"""
    SELECT cohort_week, week_n, retention_rate
    FROM `{PROJECT}.{DATASET}.retention_weekly`
    ORDER BY cohort_week, week_n
    """)
    if not ret.empty:
        ret_pivot = (
            ret.pivot(index="cohort_week", columns="week_n", values="retention_rate")
               .fillna(0)
        )
        idx = pd.IndexSlice
        styler = (
            ret_pivot.style
                .format("{:.0%}")
                .background_gradient(axis=None, cmap="Blues", subset=idx[:, :])
        )
        st.dataframe(styler, width="stretch")
    else:
        st.info("No retention data.")
except Exception as e:
    st.error(f"Retention query failed: {e}")

st.caption("Data source: BigQuery views built by dbt (ab_group, funnel_users, revenue_daily, retention_weekly, ab_metrics).")
