{{ config(materialized='view', alias='funnel_users') }}

-- PURPOSE: PER-USER FUNNEL FLAGS (VISITED, ADDED_TO_CART, CONVERTED)
WITH users AS (
  SELECT DISTINCT id AS user_id
  FROM `bigquery-public-data.thelook_ecommerce.users`
),
ev AS (
  SELECT
    user_id,
    MAX(CASE WHEN event_type = 'page_view'   THEN 1 ELSE 0 END) AS visited_flag,
    MAX(CASE WHEN event_type = 'add_to_cart' THEN 1 ELSE 0 END) AS atc_flag
  FROM `bigquery-public-data.thelook_ecommerce.events`
  GROUP BY user_id
),
conv AS (
  SELECT DISTINCT user_id
  FROM `bigquery-public-data.thelook_ecommerce.orders`
  WHERE status = 'Complete'
)
SELECT
  u.user_id,
  COALESCE(ev.visited_flag, 0) = 1 AS visited,
  COALESCE(ev.atc_flag,     0) = 1 AS added_to_cart,
  conv.user_id IS NOT NULL       AS converted
FROM users AS u
LEFT JOIN ev   USING (user_id)
LEFT JOIN conv USING (user_id)
