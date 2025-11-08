-- UI/API-friendly view of ab_group
SELECT
  user_id,
  ab_group
FROM `exec-kpi.execkpi.ab_group`
ORDER BY user_id
LIMIT 1000;
