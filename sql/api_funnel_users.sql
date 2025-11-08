-- UI/API-friendly view of funnel_users
SELECT
  user_id,
  visited,
  added_to_cart,
  converted
FROM `exec-kpi.execkpi.funnel_users`
ORDER BY user_id
LIMIT 1000;
