-- Purpose: uplift and bucket-balance (SRM) check for A/B
-- Reads: exec-kpi.execkpi.vw_ab_metrics, exec-kpi.execkpi.vw_ab_group

-- Uplift (absolute and relative)
WITH m AS (
  SELECT * FROM `exec-kpi.execkpi.vw_ab_metrics`
),
rates AS (
  SELECT
    MAX(IF(ab_group='A', conversion_rate, NULL)) AS cr_A,
    MAX(IF(ab_group='B', conversion_rate, NULL)) AS cr_B
  FROM m
)
SELECT
  cr_A,
  cr_B,
  cr_B - cr_A AS abs_uplift,
  SAFE_DIVIDE(cr_B - cr_A, cr_A) AS rel_uplift
FROM rates;

-- SRM: bucket shares should be ~0.5 each
SELECT
  COUNTIF(ab_group='A')/COUNT(*) AS share_A,
  COUNTIF(ab_group='B')/COUNT(*) AS share_B
FROM `exec-kpi.execkpi.vw_ab_group`;
