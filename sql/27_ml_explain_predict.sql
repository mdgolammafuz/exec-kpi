-- Purpose: per-user explanations (top 5 features) + predicted class & probability
-- Notes: ML.EXPLAIN_PREDICT returns:
--   predicted_<label>, probability, top_feature_attributions (array of {feature, attribution})
--   Ref: BigQuery ML docs
SELECT
  user_id,
  will_convert_14d AS actual_label,
  predicted_will_convert_14d     AS predicted_label,
  probability,
  top_feature_attributions       -- ARRAY<STRUCT<feature STRING, attribution FLOAT64>>
FROM ML.EXPLAIN_PREDICT(
  MODEL `exec-kpi.execkpi.xgb_propensity`,
  (SELECT * FROM `exec-kpi.execkpi.vw_features_conversion` LIMIT 50),
  STRUCT(5 AS top_k_features)
);
