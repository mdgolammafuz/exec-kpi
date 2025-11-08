-- UI/API-friendly view of retention_weekly
SELECT
  cohort_week,
  week_n,
  retention_rate
FROM `exec-kpi.execkpi.retention_weekly`
ORDER BY cohort_week, week_n;
