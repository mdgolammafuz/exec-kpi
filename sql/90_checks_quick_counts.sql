-- Purpose: quick sanity counts you can paste into README

-- Last 7 days KPIs
SELECT *
FROM `exec-kpi.execkpi.vw_revenue_daily`
ORDER BY day DESC
LIMIT 7;

-- Funnel counts
SELECT
  SUM(CAST(saw_landing AS INT64))  AS landing_users,
  SUM(CAST(saw_product AS INT64))  AS product_users,
  SUM(CAST(saw_cart AS INT64))     AS cart_users,
  SUM(CAST(converted AS INT64))    AS purchasers
FROM `exec-kpi.execkpi.vw_funnel_users`;

-- A/B group metrics
SELECT *
FROM `exec-kpi.execkpi.vw_ab_metrics`;

-- Model evaluation
SELECT *
FROM ML.EVALUATE(MODEL `exec-kpi.execkpi.xgb_propensity`);
