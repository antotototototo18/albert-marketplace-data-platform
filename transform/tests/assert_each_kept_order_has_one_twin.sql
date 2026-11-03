-- Revenue is not double-counted: the export writes every order twice, and
-- int_orders__deduplicated must remove exactly one of each pair.
-- For each group of identical orders (buyer, payment, lines), the export must
-- hold exactly twice as many orders as were kept. Fewer kept means twins
-- survived (double counting); more means real orders were dropped.
-- A plain "no two kept orders within 4 days" would be wrong: 4 buyers really
-- did reorder the same basket within 4 days.
-- Returns the groups that break the rule; 0 rows = pass.
with signatures as (
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
    left join signatures as s using (order_id)
    left join {{ ref('int_orders__deduplicated') }} as d using (order_id)
    group by 1, 2, 3
)

select *
from grouped
where exported_orders != 2 * kept_orders
