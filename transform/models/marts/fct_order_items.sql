{{ config(
    partition_by={'field': 'order_date', 'data_type': 'date', 'granularity': 'month'},
    cluster_by=['p_id']
) }}
-- GRAIN: one row per product in a real order (order_id, p_id).
-- Lines of twin orders are dropped by the inner join on int_orders__country,
-- which holds real orders only. Partitioned and clustered like the L04 table
-- (docs/warehouse-tuning.md).
select
    i.order_id,
    i.p_id,
    o.order_date,
    o.country_code,
    i.qty,
    i.price_at_purchase,
    i.qty * i.price_at_purchase as line_amount
from {{ ref('stg_order_items') }} as i
join {{ ref('int_orders__country') }} as o using (order_id)
