{{ config(
    partition_by={'field': 'order_date', 'data_type': 'date', 'granularity': 'month'},
    cluster_by=['p_id']
) }}
-- GRAIN: one row per product per country per day with at least one order line.
-- Sparse: a missing row is not proof of zero demand (docs/model/star-daily-demand.md).
-- units_sold = units ORDERED: the source has no payment, cancellation or return
-- status, so this is not net sales.
select
    p_id,
    country_code,
    order_date,
    sum(qty)                  as units_sold,
    sum(line_amount)          as revenue,
    count(distinct order_id)  as order_count
from {{ ref('fct_order_items') }}
group by p_id, country_code, order_date
