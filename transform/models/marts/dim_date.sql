-- GRAIN: one row per calendar day from the first to the last order date.
-- Dense on purpose: a day with no order still exists here, so a missing day in
-- fct_daily_demand reads as "no demand recorded", not as "no such day".
with bounds as (
    select min(order_date) as first_day, max(order_date) as last_day
    from {{ ref('int_orders__deduplicated') }}
)

select
    date_day,
    extract(year from date_day)       as year,
    extract(quarter from date_day)    as quarter,
    extract(month from date_day)      as month,
    extract(day from date_day)        as day_of_month,
    extract(isoweek from date_day)    as iso_week,
    -- 1 = Monday ... 7 = Sunday
    mod(extract(dayofweek from date_day) + 5, 7) + 1 as iso_day_of_week,
    extract(dayofweek from date_day) in (1, 7)       as is_weekend
from bounds,
    unnest(generate_date_array(first_day, last_day)) as date_day
