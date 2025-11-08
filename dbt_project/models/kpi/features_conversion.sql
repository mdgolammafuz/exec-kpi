{{ config(
    materialized = 'view',
    schema = 'execkpi'
) }}

-- Purpose: feature view (R/F/M + source mix) + 14-day conversion label
-- Source: thelook_ecommerce public dataset
-- Output: exec-kpi.execkpi.features_conversion

with last_event as (
  select user_id, max(created_at) as anchor_ts
  from `bigquery-public-data.thelook_ecommerce.events`
  group by 1
),
rfm as (
  select
    u.id as user_id,
    timestamp_diff(le.anchor_ts, u.created_at, day) as days_since_signup,
    countif(o.created_at >= timestamp_sub(le.anchor_ts, interval 30 day)) as orders_30d,
    sum(
      case
        when o.created_at >= timestamp_sub(le.anchor_ts, interval 30 day)
        then oi.sale_price
        else 0
      end
    ) as revenue_30d,
    count(distinct case
      when o.created_at >= timestamp_sub(le.anchor_ts, interval 30 day)
      then o.order_id
    end) as frequency_30d
  from `bigquery-public-data.thelook_ecommerce.users` u
  join last_event le on le.user_id = u.id
  left join `bigquery-public-data.thelook_ecommerce.orders` o on o.user_id = u.id
  left join `bigquery-public-data.thelook_ecommerce.order_items` oi on oi.order_id = o.order_id
  group by 1,2
),
source_mix as (
  select
    user_id,
    safe_divide(countif(traffic_source = 'Email'),   count(*)) as pct_email,
    safe_divide(countif(traffic_source = 'Direct'),  count(*)) as pct_direct,
    safe_divide(countif(traffic_source = 'Organic'), count(*)) as pct_organic,
    safe_divide(countif(traffic_source = 'Ads'),     count(*)) as pct_ads,
    safe_divide(countif(traffic_source = 'Social'),  count(*)) as pct_social
  from `bigquery-public-data.thelook_ecommerce.events`
  group by 1
),
label as (
  select
    le.user_id,
    countif(
      o.created_at > le.anchor_ts
      and o.created_at <= timestamp_add(le.anchor_ts, interval 14 day)
    ) > 0 as will_convert_14d
  from last_event le
  left join `bigquery-public-data.thelook_ecommerce.orders` o
    on o.user_id = le.user_id
  group by 1
)
select
  r.user_id,
  r.days_since_signup,
  r.orders_30d,
  r.revenue_30d,
  r.frequency_30d,
  coalesce(s.pct_email,  0) as pct_email,
  coalesce(s.pct_direct, 0) as pct_direct,
  coalesce(s.pct_organic,0) as pct_organic,
  coalesce(s.pct_ads,    0) as pct_ads,
  coalesce(s.pct_social, 0) as pct_social,
  cast(l.will_convert_14d as int64) as will_convert_14d
from rfm r
left join source_mix s using (user_id)
join label l using (user_id)
