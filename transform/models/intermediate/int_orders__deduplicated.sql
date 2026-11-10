-- GRAIN: one row per real order.
-- The legacy export writes every order twice: same buyer, same payment, same lines,
-- the twin dated 0 to 4 days later (222,644 rows, 111,322 orders). Counting both
-- doubles revenue: EUR 39,199,900.62 as exported, EUR 19,599,950.31 once.
-- Rule: within (buyer, payment, identical lines), every second order dated at most
-- 4 days after the previous one is a twin. Checked on the 2026-10-16 export against
-- the generator's offset (twin = order_id + 111,322): same orders kept by count,
-- same revenue to the cent. The offset itself is an artefact, so it is not the rule.
with line_signatures as (
    select
        order_id,
        string_agg(
            concat(p_id, ':', cast(qty as string), ':', cast(price_at_purchase as string)), '|'
            order by p_id, qty, price_at_purchase
        ) as line_signature
    from {{ ref('stg_order_items') }}
    group by order_id
),

ranked as (
    select
        o.order_id,
        o.buyer_id,
        o.payment_id,
        o.order_date,
        row_number() over w        as rn,
        lag(o.order_date) over w   as previous_order_date
    from {{ ref('stg_orders') }} as o
    left join line_signatures as l using (order_id)
    window w as (
        partition by o.buyer_id, o.payment_id, coalesce(l.line_signature, '')
        order by o.order_date, o.order_id
    )
)

select order_id, buyer_id, payment_id, order_date
from ranked
where not (mod(rn, 2) = 0 and date_diff(order_date, previous_order_date, day) <= 4)
