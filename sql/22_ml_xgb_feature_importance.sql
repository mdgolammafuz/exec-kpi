-- Purpose: global feature importances
SELECT *
FROM ML.FEATURE_IMPORTANCE(MODEL `exec-kpi.execkpi.xgb_propensity`)
ORDER BY importance DESC;
