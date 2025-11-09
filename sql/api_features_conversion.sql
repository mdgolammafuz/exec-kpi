-- API-friendly: features_conversion
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
FROM `execkpi_execkpi.features_conversion`
LIMIT 5000;
