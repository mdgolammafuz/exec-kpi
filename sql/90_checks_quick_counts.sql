-- Purpose: quick sanity counts you can paste into README
SELECT * FROM `exec-kpi.execkpi.vw_revenue_daily` ORDER BY day DESC LIMIT 7;

SELECT
  SUM(CAST(saw_landing AS INT64))  AS landing_users,
  SUM(CAST(saw_product AS INT64))  AS product_users,
  SUM(CAST(saw_cart AS INT64))     AS cart_users,
  SUM(CAST(converted AS INT64))    AS purchasers
FROM `exec-kpi.execkpi.vw_funnel_users`;

SELECT * FROM `exec-kpi.execkpi.vw_ab_metrics`;

SELECT * FROM ML.EVALUATE(MODEL `exec-kpi.execkpi.xgb_propensity`);
