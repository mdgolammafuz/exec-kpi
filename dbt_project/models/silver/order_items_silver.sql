{{ config(materialized='view') }}

select
  *
from {{ source('thelook', 'order_items') }}
