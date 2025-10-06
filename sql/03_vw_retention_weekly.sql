-- Purpose: weekly retention by signup cohort
-- Creates: exec-kpi.execkpi.vw_retention_weekly
CREATE OR REPLACE VIEW `exec-kpi.execkpi.vw_retention_weekly` AS
WITH users_cohort AS (
  SELECT
    id AS user_id,
    DATE_TRUNC(DATE(created_at), WEEK) AS cohort_week
  FROM `bigquery-public-data.thelook_ecommerce.users`
),
activity AS (
  SELECT
    user_id,
    DATE_TRUNC(DATE(created_at), WEEK) AS active_week
  FROM `bigquery-public-data.thelook_ecommerce.events`
),
cohort_sizes AS (
  SELECT cohort_week, COUNT(DISTINCT user_id) AS cohort_size
  FROM users_cohort
  GROUP BY 1
),
actives AS (
  SELECT u.cohort_week, a.active_week, COUNT(DISTINCT a.user_id) AS active_users
  FROM users_cohort u
  JOIN activity a USING (user_id)
  GROUP BY 1,2
)
SELECT
  cohort_week,
  DATE_DIFF(active_week, cohort_week, WEEK) AS week_number,
  SAFE_DIVIDE(active_users, cohort_size)    AS retention
FROM actives
JOIN cohort_sizes USING (cohort_week)
ORDER BY cohort_week, week_number;
