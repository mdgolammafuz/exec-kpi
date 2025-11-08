-- API-friendly: funnel_users
SELECT
  user_id,
  visited,
  added_to_cart,
  converted
FROM `exec-kpi.execkpi_execkpi.funnel_users`
LIMIT 5000;
