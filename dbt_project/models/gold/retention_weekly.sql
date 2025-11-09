{{ config(materialized='view', alias='retention_weekly') }}

with cohorts as (
  select
    u.id as user_id,
    date_trunc(date(u.created_at), week(monday)) as cohort_week
  from {{ ref('users_silver') }} u
),
activity as (
  select
    e.user_id,
    date_trunc(date(e.created_at), week(monday)) as activity_week
  from {{ ref('events_silver') }} e
  where e.user_id is not null
),
joined as (
  select
    c.cohort_week,
    a.user_id,
    cast(date_diff(a.activity_week, c.cohort_week, week) as int64) as week_n
  from cohorts c
  join activity a
    on a.user_id = c.user_id
  where date_diff(a.activity_week, c.cohort_week, week) between 0 and 12
),
cohort_sizes as (
  select cohort_week, count(distinct user_id) as cohort_users
  from cohorts
  group by cohort_week
),
retention as (
  select
    j.cohort_week,
    j.week_n,
    count(distinct j.user_id) as active_users
  from joined j
  group by j.cohort_week, j.week_n
)
select
  r.cohort_week,
  r.week_n,
  safe_divide(r.active_users, cs.cohort_users) as retention_rate
from retention r
join cohort_sizes cs
  on cs.cohort_week = r.cohort_week
order by cohort_week, week_n
