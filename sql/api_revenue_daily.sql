-- Readable daily KPI for the UI/API
SELECT
  day,
  revenue,
  orders,
  aov
FROM `exec-kpi.execkpi.revenue_daily`
WHERE day BETWEEN @start AND @end
ORDER BY day;
