# ExecKPI – BI Layer

This document describes how the BI/reporting part of the project should consume data that is modeled in dbt and refreshed by Airflow.

## 1. Location of data

- **Project:** `exec-kpi`  
- **Dataset:** `execkpi_execkpi`

dbt builds the following views in that dataset, and all BI tools should read from these views, not from the underlying public TheLook tables.

## 2. Views intended for BI

These views are created by dbt and refreshed by the Airflow DAG `execkpi_daily`:

1. `execkpi_execkpi.revenue_daily`  
   Daily orders, revenue, and AOV.
2. `execkpi_execkpi.funnel_users`  
   One row per user with funnel flags (visited, added_to_cart, converted).
3. `execkpi_execkpi.retention_weekly`  
   Cohort-based weekly retention (cohort_week × week_n).
4. `execkpi_execkpi.ab_metrics`  
   Aggregated A/B metrics per group (users, converters, conversion_rate).
5. `execkpi_execkpi.ab_group`  
   Deterministic group assignment, used to support the A/B view.
6. `execkpi_execkpi.features_conversion`  
   Feature table with the `will_convert_14d` label (optional for BI, useful for inspection tables).

These views together cover trends, user behavior, retention, experimentation, and model-ready data.

## 3. Example: Looker Studio dashboard

We can build a simple dashboard in Looker Studio using only the dataset above.

1. Create a new report in Looker Studio.
2. Add a **BigQuery** data source and select:
   - Project: `exec-kpi`
   - Dataset: `execkpi_execkpi`
3. Add the following charts:

**Chart A – Revenue over time**
- Source: `revenue_daily`
- Dimension: `day`
- Metrics: `revenue`, `orders`, `aov`
- Visualization: time series

**Chart B – Funnel status**
- Source: `funnel_users`
- Show counts or percentages of users for visited, added_to_cart, converted
- Visualization: table or bar

**Chart C – Cohort retention**
- Source: `retention_weekly`
- Dimension: `cohort_week`
- Breakdown: `week_n`
- Metric: `retention_rate`
- Visualization: table or pivot

**Chart D – A/B metrics**
- Source: `ab_metrics`
- Dimension: `ab_group`
- Metrics: `users`, `converters`, `conversion_rate`
- Visualization: table or bar

This produces a dashboard that is aligned with the modeled warehouse and can be explained easily.

## 4. Refresh and lineage

Data for the BI layer is refreshed by:

- **DAG:** `airflow/dags/execkpi_dag.py`
- **Steps:**
  1. `dbt run` (rebuilds the views in `execkpi_execkpi`)
  2. `dbt test --select gold` (basic quality checks)
  3. `python backend/train_explain.py` (ML artifacts; same dataset)

Because the BI views are the same ones rebuilt by this DAG, we can state that the dashboard reflects the current modeled state.

## 5. Alignment with other components

- The API (`backend/main.py`) executes only the SQL files in `sql/api_*.sql`, which also read from `execkpi_execkpi.*`.
- The ML trainer (`backend/train_explain.py`) reads from `execkpi_execkpi.features_conversion`.
- The BI layer described here reads from the same dataset.

This ensures that API, ML, and BI all consume the same governed layer.
