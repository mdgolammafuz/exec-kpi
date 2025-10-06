-- Purpose: SHAP-style global attributions (mean absolute)
SELECT *
FROM ML.GLOBAL_EXPLAIN(MODEL `exec-kpi.execkpi.xgb_propensity`)
ORDER BY mean_abs_shap_value DESC
LIMIT 10;
