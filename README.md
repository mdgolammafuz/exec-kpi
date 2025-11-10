# ExecKPI — Product KPIs with BigQuery, dbt, and Streamlit

[![backend-ci](https://github.com/mdgolammafuz/exec-kpi/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/mdgolammafuz/exec-kpi/actions/workflows/backend-ci.yml)


## What this repository provides

We ship a focused analytics stack that answers three product questions:

- **Revenue trend** over time and change vs. a comparable window  
- **A/B test conversion** with p‑value, confidence interval, and split‑health (SRM)  
- **Weekly retention** as a cohort × week heatmap

Warehouse: **BigQuery**. Transformation/tests: **dbt**. UI: **Streamlit**.  
CI runs linting and basic dbt checks.

## Live demo

> **Link:** _to be added after Streamlit Community Cloud deploy_

---

## How to run locally

```bash
# 0) Clone
git clone https://github.com/mdgolammafuz/exec-kpi.git
cd exec-kpi

# 1) Python env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2) GCP auth + project
gcloud auth application-default login
gcloud config set project exec-kpi

# 3) Build analytics layer
cd dbt_project
dbt run
dbt test
cd ..

# 4) Start the app
python -m streamlit run app/app.py
# Open http://localhost:8501
```

---

## Folder structure

```
.
├─ app/
│  └─ app.py                # Streamlit UI: revenue chart, A/B significance (z-test + SRM), retention heatmap
├─ dbt_project/
│  ├─ models/kpi/
│  │  ├─ revenue_daily.sql          # Daily revenue aggregation (source → daily metric)
│  │  ├─ funnel_users.sql           # Per-user funnel flags (visited, added_to_cart, converted)
│  │  ├─ ab_group.sql               # A/B group assignment (A/B split)
│  │  ├─ ab_metrics.sql             # Users, converters, conversion_rate per group
│  │  └─ retention_weekly.sql       # Cohort week × week_n retention rates
│  └─ tests/                        # Basic dbt schema/data tests (not_null, accepted_values)
├─ airflow/
│  └─ dags/execkpi_daily.py         # (Optional) Daily job: dbt run + BQML retrain
├─ .github/workflows/ci.yml         # Lint + dbt parse/tests (CI badge at top of README)
├─ requirements.txt                 # App + dbt + BigQuery client deps
└─ docs/images/                     # Repo-hosted screenshots used in README
```

> Notes  
> • We keep only the source layout in the tree; runtime artifacts (dbt `target/`, logs, `__pycache__`, local Airflow SQLite DB) are not part of this view.  
> • `sql/` files (if present) mirror dbt logic and BQML examples for reference; the Streamlit app reads the **dbt** models in `dbt_project/models/kpi/`.

---

## CLI sanity checks

Set once per shell:
```bash
export PROJECT=exec-kpi
export DATASET=execkpi_execkpi
export START=2025-09-14
export END=2025-10-14
```

**Revenue: current vs previous same-length window**
```bash
bq query --use_legacy_sql=false "
DECLARE d_start DATE DEFAULT DATE('$START');
DECLARE d_end   DATE DEFAULT DATE('$END');
DECLARE win_days INT64 DEFAULT DATE_DIFF(d_end,d_start,DAY)+1;
WITH cur AS (
  SELECT SUM(revenue) cur_rev
  FROM \`$PROJECT.$DATASET.revenue_daily\`
  WHERE day BETWEEN d_start AND d_end
),
prev AS (
  SELECT SUM(revenue) prev_rev
  FROM \`$PROJECT.$DATASET.revenue_daily\`
  WHERE day BETWEEN DATE_SUB(d_start,INTERVAL win_days DAY)
                  AND DATE_SUB(d_end,INTERVAL win_days DAY)
)
SELECT cur_rev, prev_rev, cur_rev - prev_rev AS delta,
SAFE_DIVIDE(cur_rev - prev_rev, prev_rev)*100 AS delta_pct
FROM cur, prev;"
```

**A/B group counts**
```bash
bq query --use_legacy_sql=false "
SELECT
  SUM(CASE WHEN ab_group='A' THEN users END)      AS n_c,
  SUM(CASE WHEN ab_group='B' THEN users END)      AS n_t,
  SUM(CASE WHEN ab_group='A' THEN converters END) AS x_c,
  SUM(CASE WHEN ab_group='B' THEN converters END) AS x_t
FROM \`$PROJECT.$DATASET.ab_metrics\`;"
```

**Retention coverage**
```bash
bq query --use_legacy_sql=false "
SELECT
  COUNT(*) AS row_count,
  MIN(week_n) AS min_week,
  MAX(week_n) AS max_week,
  MIN(retention_rate) AS min_ret,
  MAX(retention_rate) AS max_ret
FROM \`$PROJECT.$DATASET.retention_weekly\`;"
```

---

## dbt model intent (short)

- `revenue_daily.sql` — daily revenue series  
- `funnel_users.sql` — one row per user with funnel flags  
- `ab_group.sql` — A/B assignment  
- `ab_metrics.sql` — users, converters, conversion rate by group  
- `retention_weekly.sql` — cohort_week × week_n retention

---

## CI

- `flake8` lint for the Streamlit app and basic Python checks  
- dbt parse and schema tests  
- Status is visible in the badge at the top of this file

---

## Screenshots (to add)

Place PNGs under `docs/images/` and reference them here:

- Revenue trend: `docs/images/01_revenue.png`  
- A/B conversion and significance: `docs/images/02_ab.png`  
- Retention heatmap: `docs/images/03_retention.png`

We will capture them after deploying the Streamlit app and verifying numbers.

---

## BI dashboard

A sample Looker Studio dashboard built on the dbt gold views (`execkpi_execkpi`) is available here:

[ExecKPI – Governed Analytics](https://lookerstudio.google.com/reporting/c0c4c083-3949-4f45-8735-69f3f0b67d9b)


---

## Trade-offs and next steps

**Trade-offs:** no infra-as-code or Cloud Run deployment here to avoid billing and key management in public. Streamlit UI is intentionally minimal. dbt tests are basic.

**Next steps:** host on Streamlit Community Cloud (with Secrets), optionally add Looker tiles, add Terraform for BigQuery resources, and add lightweight logging of query timings to a table.
