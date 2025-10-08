{{ config(materialized='view') }}

-- Per-user funnel flags; conversion = has a completed order
WITH e AS (
  SELECT
    user_id,
    ARRAY_AGG(DISTINCT event_type IGNORE NULLS) AS events
  FROM `bigquery-public-data.thelook_ecommerce.events`
  WHERE user_id IS NOT NULL          -- <<< fix: drop null user_id rows
  GROUP BY 1
),
purchasers AS (
  SELECT DISTINCT user_id
  FROM `bigquery-public-data.thelook_ecommerce.orders`
  WHERE status = 'Complete'
)
SELECT
  e.user_id,
  ('landing'  IN UNNEST(events)) AS saw_landing,
  ('product'  IN UNNEST(events)) AS saw_product,
  ('cart'     IN UNNEST(events)) AS saw_cart,
  IF(p.user_id IS NULL, FALSE, TRUE) AS converted
FROM e
LEFT JOIN purchasers p USING (user_id)
