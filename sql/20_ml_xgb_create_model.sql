-- Purpose: train XGBoost classifier in BigQuery ML (global explain enabled)
-- Creates: exec-kpi.execkpi.xgb_propensity (MODEL)
CREATE OR REPLACE MODEL `exec-kpi.execkpi.xgb_propensity`
OPTIONS(
  MODEL_TYPE         = 'BOOSTED_TREE_CLASSIFIER',
  INPUT_LABEL_COLS   = ['will_convert_14d'],
  MAX_ITERATIONS     = 50,
  EARLY_STOP         = TRUE,
  DATA_SPLIT_METHOD  = 'AUTO_SPLIT',
  ENABLE_GLOBAL_EXPLAIN = TRUE
) AS
SELECT
  days_since_signup,
  orders_30d,
  revenue_30d,
  frequency_30d,
  pct_email, pct_direct, pct_organic, pct_ads, pct_social,
  will_convert_14d
FROM `exec-kpi.execkpi.vw_features_conversion`;
