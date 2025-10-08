-- Purpose: per-group conversion rate using funnel flags
-- Creates: exec-kpi.execkpi.vw_ab_metrics
CREATE OR REPLACE VIEW `exec-kpi.execkpi.vw_ab_metrics` AS
WITH base AS (
  SELECT g.ab_group, f.converted
  FROM `exec-kpi.execkpi.vw_funnel_users` f
  JOIN `exec-kpi.execkpi.vw_ab_group`   g USING (user_id)
)
SELECT
  ab_group,
  COUNT(*)                                      AS users,
  SUM(CAST(converted AS INT64))                 AS converters,
  SAFE_DIVIDE(SUM(CAST(converted AS INT64)), COUNT(*)) AS conversion_rate
FROM base
GROUP BY ab_group;
