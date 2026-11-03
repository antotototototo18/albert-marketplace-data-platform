-- GRAIN: one row per real order, with the country it is attributed to.
-- Orders to addresses fans out: a buyer has 1 to 3 addresses. The data carries the
-- rule that picks one: exactly one is_default address per buyer (100,000 of 100,000),
-- tested on stg_customer_shipping. Filtering on it BEFORE the join keeps one row
-- per order; the unique test on order_id fails the day that stops being true.
-- The country is a proxy: the buyer's CURRENT default address, not the address
-- the order shipped to, which the legacy schema does not keep (docs/model/star-daily-demand.md).
-- An order with no default address keeps its units, under UNKNOWN.
with default_country as (
    select
        cs.c_id,
        sd.country_code
    from {{ ref('stg_customer_shipping') }} as cs
    join {{ ref('stg_shipping_details') }} as sd using (address_id)
    where cs.is_default
)

select
    o.order_id,
    o.order_date,
    coalesce(dc.country_code, 'UNKNOWN') as country_code
from {{ ref('int_orders__deduplicated') }} as o
left join default_country as dc
    on dc.c_id = o.buyer_id
