-- API-friendly: retention_weekly
SELECT
  cohort_week,
  week_n,
  retention_rate
FROM `exec-kpi.execkpi_execkpi.retention_weekly`
ORDER BY cohort_week, week_n;
