{{ config(materialized='view') }}

select
  *
from {{ source('thelook', 'orders') }}
