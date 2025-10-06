-- Purpose: deterministic A/B assignment by user
-- Creates: exec-kpi.execkpi.vw_ab_group
CREATE OR REPLACE VIEW `exec-kpi.execkpi.vw_ab_group` AS
SELECT
  u.id AS user_id,
  CASE
    WHEN MOD(ABS(FARM_FINGERPRINT(CAST(u.id AS STRING))), 100) < 50 THEN 'A'
    ELSE 'B'
  END AS ab_group
FROM `bigquery-public-data.thelook_ecommerce.users` u;
