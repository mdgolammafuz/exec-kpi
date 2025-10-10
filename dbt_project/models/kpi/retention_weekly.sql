{{ config(materialized='view', alias='retention_weekly') }}

-- PURPOSE: WEEKLY COHORT RETENTION (BASED ON COMPLETED ORDERS)
WITH first_orders AS (
  SELECT
    user_id,
    MIN(DATE(created_at)) AS first_order_date
  FROM `bigquery-public-data.thelook_ecommerce.orders`
  WHERE status = 'Complete'
  GROUP BY user_id
),
all_orders AS (
  SELECT
    user_id,
    DATE(created_at) AS order_date
  FROM `bigquery-public-data.thelook_ecommerce.orders`
  WHERE status = 'Complete'
)
SELECT
  DATE_TRUNC(first_order_date, WEEK(MONDAY)) AS cohort_week,
  DATE_TRUNC(order_date,       WEEK(MONDAY)) AS activity_week,
  COUNT(DISTINCT a.user_id)                  AS active_users
FROM first_orders f
JOIN all_orders  a
  ON a.user_id = f.user_id
GROUP BY cohort_week, activity_week
ORDER BY cohort_week, activity_week
