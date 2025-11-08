-- UI/API-friendly view of ab_metrics
SELECT
  ab_group,
  users,
  converters,
  conversion_rate
FROM `exec-kpi.execkpi.ab_metrics`
ORDER BY ab_group;
