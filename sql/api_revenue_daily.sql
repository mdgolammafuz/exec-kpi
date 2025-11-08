-- API-friendly: revenue_daily
SELECT
  day,
  orders,
  revenue,
  aov
FROM `exec-kpi.execkpi_execkpi.revenue_daily`
WHERE (@start IS NULL OR day >= @start)
  AND (@end   IS NULL OR day <= @end)
ORDER BY day;
