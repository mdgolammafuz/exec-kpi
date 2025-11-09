{{ config(materialized='view', alias='funnel_users') }}

-- PURPOSE: PER-USER FUNNEL FLAGS (VISITED, ADDED_TO_CART, CONVERTED)
with users as (
  select distinct id as user_id
  from {{ ref('users_silver') }}
),
ev as (
  select
    user_id,
    max(case when event_type = 'page_view'   then 1 else 0 end) as visited_flag,
    max(case when event_type = 'add_to_cart' then 1 else 0 end) as atc_flag
  from {{ ref('events_silver') }}
  group by user_id
),
conv as (
  select distinct user_id
  from {{ ref('orders_silver') }}
  where status = 'Complete'
)
select
  u.user_id,
  coalesce(ev.visited_flag, 0) = 1 as visited,
  coalesce(ev.atc_flag,     0) = 1 as added_to_cart,
  conv.user_id is not null       as converted
from users u
left join ev   using (user_id)
left join conv using (user_id)