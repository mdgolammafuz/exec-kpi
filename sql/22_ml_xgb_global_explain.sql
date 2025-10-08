-- Purpose: global SHAP-style attributions (which features matter overall)
-- Reads: model exec-kpi.execkpi.xgb_propensity (must be trained with ENABLE_GLOBAL_EXPLAIN=TRUE)
SELECT
  feature,
  attribution
FROM ML.GLOBAL_EXPLAIN(MODEL `exec-kpi.execkpi.xgb_propensity`)
ORDER BY attribution DESC
LIMIT 20;
