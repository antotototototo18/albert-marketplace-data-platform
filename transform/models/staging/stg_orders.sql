-- Drops unnamed_0: the export's row index (0 to 222,643), no business meaning.
-- Drops discount_id: empty on all 222,644 rows, and the discount table has 0 rows.
-- Casts order_id and payment_id to INT64 and order_date to DATE (bronze is all STRING).
-- Leaves the twin orders alone: telling them apart needs order_items, so it is a
-- join, and lives in int_orders__deduplicated.
select
    cast(order_id as int64)   as order_id,
    buyer_id,
    cast(payment_id as int64) as payment_id,
    cast(order_date as date)  as order_date
from {{ source('bronze_legacy', 'orders') }}
