{{ config(materialized='view', alias='ab_metrics') }}

-- PURPOSE: PER-GROUP CONVERSION METRICS
with base as (
  select
    g.ab_group,
    f.converted
  from {{ ref('funnel_users') }} as f
  join {{ ref('ab_group') }} as g
    on f.user_id = g.user_id
)
select
  ab_group,
  count(*) as users,
  sum(cast(converted as int64)) as converters,
  safe_divide(sum(cast(converted as int64)), count(*)) as conversion_rate
from base
group by ab_group
order by ab_group