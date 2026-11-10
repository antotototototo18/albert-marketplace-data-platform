-- Casts order_id and qty to INT64 and price_at_purchase to NUMERIC: every price
-- has exactly two decimals, so NUMERIC is exact (bronze is all STRING).
-- Keeps p_id as STRING: 6 product ids start with 0.
-- Leaves alone the 30 lines priced 0.00: they carry units the buyer did order,
-- and no column says whether they are gifts or errors (docs/data-dictionary.md).
-- qty runs from 1 to 12, not 1 to 9 as dictionary v1 said; nothing to fix.
select
    cast(order_id as int64)            as order_id,
    p_id,
    cast(qty as int64)                 as qty,
    cast(price_at_purchase as numeric) as price_at_purchase
from {{ source('bronze_legacy', 'order_items') }}
