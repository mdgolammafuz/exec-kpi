-- Purpose: per-row SHAP-style explanations for sample users
SELECT *
FROM ML.EXPLAIN_PREDICT(
  MODEL `exec-kpi.execkpi.xgb_propensity`,
  (SELECT * FROM `exec-kpi.execkpi.vw_features_conversion` LIMIT 50)
);
