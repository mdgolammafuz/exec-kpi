-- Purpose: per-user funnel flags (landing/product/cart/purchase)
-- Creates: exec-kpi.execkpi.vw_funnel_users
CREATE OR REPLACE VIEW `exec-kpi.execkpi.vw_funnel_users` AS
WITH e AS (
  SELECT
    user_id,
    ARRAY_AGG(DISTINCT event_type IGNORE NULLS) AS events
  FROM `bigquery-public-data.thelook_ecommerce.events`
  GROUP BY 1
)
SELECT
  user_id,
  ('landing'  IN UNNEST(events)) AS saw_landing,
  ('product'  IN UNNEST(events)) AS saw_product,
  ('cart'     IN UNNEST(events)) AS saw_cart,
  ('purchase' IN UNNEST(events)) AS converted
FROM e;
