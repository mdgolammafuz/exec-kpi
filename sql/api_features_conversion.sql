-- UI/API-friendly view of ML features
SELECT
  user_id,
  days_since_signup,
  orders_30d,
  revenue_30d,
  frequency_30d,
  pct_email,
  pct_direct,
  pct_organic,
  pct_ads,
  pct_social,
  will_convert_14d
FROM `exec-kpi.execkpi.features_conversion`
ORDER BY user_id
LIMIT 500;
