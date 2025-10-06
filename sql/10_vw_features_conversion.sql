-- Purpose: feature view (R/F/M + source mix) + 14-day conversion label
-- Creates: exec-kpi.execkpi.vw_features_conversion
CREATE OR REPLACE VIEW `exec-kpi.execkpi.vw_features_conversion` AS
WITH last_event AS (
  SELECT user_id, MAX(created_at) AS anchor_ts
  FROM `bigquery-public-data.thelook_ecommerce.events`
  GROUP BY 1
),
rfm AS (
  SELECT
    u.id AS user_id,
    TIMESTAMP_DIFF(le.anchor_ts, u.created_at, DAY)                    AS days_since_signup,
    COUNTIF(o.created_at >= TIMESTAMP_SUB(le.anchor_ts, INTERVAL 30 DAY)) AS orders_30d,
    SUM(CASE WHEN o.created_at >= TIMESTAMP_SUB(le.anchor_ts, INTERVAL 30 DAY)
             THEN oi.sale_price ELSE 0 END)                            AS revenue_30d,
    COUNT(DISTINCT CASE WHEN o.created_at >= TIMESTAMP_SUB(le.anchor_ts, INTERVAL 30 DAY)
                        THEN o.order_id END)                           AS frequency_30d
  FROM `bigquery-public-data.thelook_ecommerce.users` u
  JOIN last_event le ON le.user_id = u.id
  LEFT JOIN `bigquery-public-data.thelook_ecommerce.orders` o ON o.user_id = u.id
  LEFT JOIN `bigquery-public-data.thelook_ecommerce.order_items` oi ON oi.order_id = o.order_id
  GROUP BY 1,2
),
source_mix AS (
  SELECT
    user_id,
    SAFE_DIVIDE(COUNTIF(traffic_source = 'Email'),   COUNT(*)) AS pct_email,
    SAFE_DIVIDE(COUNTIF(traffic_source = 'Direct'),  COUNT(*)) AS pct_direct,
    SAFE_DIVIDE(COUNTIF(traffic_source = 'Organic'), COUNT(*)) AS pct_organic,
    SAFE_DIVIDE(COUNTIF(traffic_source = 'Ads'),     COUNT(*)) AS pct_ads,
    SAFE_DIVIDE(COUNTIF(traffic_source = 'Social'),  COUNT(*)) AS pct_social
  FROM `bigquery-public-data.thelook_ecommerce.events`
  GROUP BY 1
),
label AS (
  SELECT
    le.user_id,
    COUNTIF(o.created_at > le.anchor_ts
            AND o.created_at <= TIMESTAMP_ADD(le.anchor_ts, INTERVAL 14 DAY)) > 0
      AS will_convert_14d
  FROM last_event le
  LEFT JOIN `bigquery-public-data.thelook_ecommerce.orders` o
    ON o.user_id = le.user_id
  GROUP BY 1
)
SELECT
  r.user_id,
  r.days_since_signup,
  r.orders_30d,
  r.revenue_30d,
  r.frequency_30d,
  COALESCE(s.pct_email,  0) AS pct_email,
  COALESCE(s.pct_direct, 0) AS pct_direct,
  COALESCE(s.pct_organic,0) AS pct_organic,
  COALESCE(s.pct_ads,    0) AS pct_ads,
  COALESCE(s.pct_social, 0) AS pct_social,
  CAST(l.will_convert_14d AS INT64) AS will_convert_14d
FROM rfm r
LEFT JOIN source_mix s USING (user_id)
JOIN label l USING (user_id);
