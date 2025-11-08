-- API-friendly: ab_metrics
SELECT
  ab_group,
  users,
  converters,
  conversion_rate
FROM `exec-kpi.execkpi_execkpi.ab_metrics`
ORDER BY ab_group;
