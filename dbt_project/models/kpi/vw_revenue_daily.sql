{{ config(materialized='view') }}

-- Daily revenue/orders/AOV (completed orders)
SELECT
  DATE_TRUNC(o.created_at, DAY) AS day,
  COUNT(DISTINCT o.order_id)    AS orders,
  SUM(oi.sale_price)            AS revenue,
  AVG(oi.sale_price)            AS aov
FROM `bigquery-public-data.thelook_ecommerce.orders` o
JOIN `bigquery-public-data.thelook_ecommerce.order_items` oi USING(order_id)
WHERE o.status = 'Complete'
GROUP BY 1
ORDER BY 1
