{{ config(materialized='view', alias='revenue_daily') }}

-- DAILY ORDERS / REVENUE / AOV (COMPLETED ORDERS)
WITH items AS (
  SELECT
    DATE(o.created_at) AS day,
    o.status,
    oi.sale_price
  FROM `bigquery-public-data.thelook_ecommerce.orders` AS o
  JOIN `bigquery-public-data.thelook_ecommerce.order_items` AS oi
    ON o.order_id = oi.order_id
)
SELECT
  day,
  COUNTIF(status = 'Complete') AS orders,
  SUM(CASE WHEN status = 'Complete' THEN sale_price ELSE 0 END) AS revenue,
  SAFE_DIVIDE(
    SUM(CASE WHEN status = 'Complete' THEN sale_price ELSE 0 END),
    NULLIF(COUNTIF(status = 'Complete'), 0)
  ) AS aov
FROM items
GROUP BY day
ORDER BY day
