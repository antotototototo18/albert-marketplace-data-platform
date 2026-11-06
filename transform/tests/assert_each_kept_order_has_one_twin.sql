-- Revenue is not double-counted: the export writes every order twice, and
-- int_orders__deduplicated must remove exactly one of each pair.
-- For each group of identical orders (buyer, payment, lines), the export must
-- hold exactly twice as many orders as were kept. Fewer kept means twins
-- survived (double counting); more means real orders were dropped.
-- A plain "no two kept orders within 4 days" would be wrong: 4 buyers really
-- did reorder the same basket within 4 days.
-- Returns the groups that break the rule; 0 rows = pass.
-- Scope: the legacy export only, the rows carrying its CSV row index (unnamed_0).
-- Orders extracted by the L07 DAG are not doubled (426 of the 468 orders of
-- 2026-09-15/16 are alone in their group), so the rule does not describe them.
with legacy_orders as (
    select cast(order_id as int64) as order_id
    from {{ source('bronze_legacy', 'orders') }}
    where unnamed_0 is not null
),

signatures as (
    select
        order_id,
        string_agg(
            concat(p_id, ':', cast(qty as string), ':', cast(price_at_purchase as string)), '|'
            order by p_id, qty, price_at_purchase
        ) as line_signature
    from {{ ref('stg_order_items') }}
    group by order_id
),

grouped as (
    select
        o.buyer_id,
        o.payment_id,
        coalesce(s.line_signature, '')                   as line_signature,
        count(*)                                         as exported_orders,
        countif(d.order_id is not null)                  as kept_orders
    from {{ ref('stg_orders') }} as o
    join legacy_orders using (order_id)
    left join signatures as s using (order_id)
    left join {{ ref('int_orders__deduplicated') }} as d using (order_id)
    group by 1, 2, 3
)

select *
from grouped
where exported_orders != 2 * kept_orders
