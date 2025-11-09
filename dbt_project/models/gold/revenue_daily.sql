{{ config(materialized='view', alias='revenue_daily') }}

-- DAILY ORDERS / REVENUE / AOV (COMPLETED ORDERS)
with items as (
  select
    date(o.created_at) as day,
    o.status,
    oi.sale_price
  from {{ ref('orders_silver') }} as o
  join {{ ref('order_items_silver') }} as oi
    on o.order_id = oi.order_id
)
select
  day,
  countif(status = 'Complete') as orders,
  sum(case when status = 'Complete' then sale_price else 0 end) as revenue,
  safe_divide(
    sum(case when status = 'Complete' then sale_price else 0 end),
    nullif(countif(status = 'Complete'), 0)
  ) as aov
from items
group by day
order by day
