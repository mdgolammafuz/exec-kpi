{{ config(materialized='view', alias='ab_metrics') }}

-- PURPOSE: PER-GROUP CONVERSION METRICS
WITH base AS (
  SELECT
    g.ab_group,
    f.converted
  FROM {{ ref('funnel_users') }} AS f
  JOIN {{ ref('ab_group') }}     AS g USING (user_id)
)
SELECT
  ab_group,
  COUNT(*)                                      AS users,
  SUM(CAST(converted AS INT64))                 AS converters,
  SAFE_DIVIDE(SUM(CAST(converted AS INT64)), COUNT(*)) AS conversion_rate
FROM base
GROUP BY ab_group
ORDER BY ab_group
