{{ config(materialized='view', alias='ab_group') }}

-- PURPOSE: DETERMINISTIC 50/50 A/B ASSIGNMENT PER USER
with users as (
  select id as user_id
  from {{ ref('users_silver') }}
)
select
  user_id,
  case
    when mod(abs(farm_fingerprint(cast(user_id as string))), 100) < 50 then 'A'
    else 'B'
  end as ab_group
from users
