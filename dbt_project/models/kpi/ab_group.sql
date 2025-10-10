{{ config(materialized='view', alias='ab_group') }}

-- PURPOSE: DETERMINISTIC 50/50 A/B ASSIGNMENT PER USER
SELECT
  u.id AS user_id,
  CASE
    WHEN MOD(ABS(FARM_FINGERPRINT(CAST(u.id AS STRING))), 100) < 50 THEN 'A'
    ELSE 'B'
  END AS ab_group
FROM `bigquery-public-data.thelook_ecommerce.users` AS u
