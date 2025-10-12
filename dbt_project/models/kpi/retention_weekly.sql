{{ config(materialized='view', alias='retention_weekly') }}

WITH cohorts AS (
  SELECT
    u.id AS user_id,
    DATE_TRUNC(DATE(u.created_at), WEEK(MONDAY)) AS cohort_week
  FROM `bigquery-public-data.thelook_ecommerce.users` u
),
activity AS (
  SELECT
    e.user_id,
    DATE_TRUNC(DATE(e.created_at), WEEK(MONDAY)) AS activity_week
  FROM `bigquery-public-data.thelook_ecommerce.events` e
  WHERE e.user_id IS NOT NULL
),
joined AS (
  SELECT
    c.cohort_week,
    a.user_id,
    CAST(DATE_DIFF(a.activity_week, c.cohort_week, WEEK) AS INT64) AS week_n
  FROM cohorts c
  JOIN activity a
    ON a.user_id = c.user_id
  WHERE DATE_DIFF(a.activity_week, c.cohort_week, WEEK) BETWEEN 0 AND 12
),
cohort_sizes AS (
  SELECT cohort_week, COUNT(DISTINCT user_id) AS cohort_users
  FROM cohorts
  GROUP BY cohort_week
),
retention AS (
  SELECT
    j.cohort_week,
    j.week_n,
    COUNT(DISTINCT j.user_id) AS active_users
  FROM joined j
  GROUP BY j.cohort_week, j.week_n
)
SELECT
  r.cohort_week,
  r.week_n,
  SAFE_DIVIDE(r.active_users, cs.cohort_users) AS retention_rate
FROM retention r
JOIN cohort_sizes cs
  ON cs.cohort_week = r.cohort_week
ORDER BY cohort_week, week_n
