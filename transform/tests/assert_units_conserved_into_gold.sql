-- No join on the way to gold adds or loses an order line.
-- Starting point: the lines of real orders (twins removed). Each gold step must
-- hold the same number of lines and the same units. A fan-out raises the
-- numbers; an inner join that drops orders without a country lowers them.
-- Returns one row per step that disagrees; 0 rows = pass.
with expected as (
    select count(*) as lines, sum(i.qty) as units
    from {{ ref('stg_order_items') }} as i
    join {{ ref('int_orders__deduplicated') }} as o using (order_id)
),

observed as (
    select 'fct_order_items' as model, count(*) as lines, sum(qty) as units
    from {{ ref('fct_order_items') }}
    union all
    select 'fct_daily_demand', null, sum(units_sold)
    from {{ ref('fct_daily_demand') }}
)

select
    observed.model,
    expected.lines as expected_lines,
    observed.lines as observed_lines,
    expected.units as expected_units,
    observed.units as observed_units
from observed
cross join expected
where observed.units != expected.units
   or (observed.lines is not null and observed.lines != expected.lines)
