{{ config(materialized='view') }}

select
  *
from {{ source('thelook', 'events') }}
