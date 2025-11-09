-- API-friendly: funnel_users
SELECT
  user_id,
  visited,
  added_to_cart,
  converted
FROM `execkpi_execkpi.funnel_users`
LIMIT 5000;
