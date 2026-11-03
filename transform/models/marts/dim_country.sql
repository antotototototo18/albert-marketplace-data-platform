-- GRAIN: one row per country code, plus UNKNOWN for orders whose buyer has no
-- default address. The codes come from the one mapping, in stg_shipping_details.
select distinct
    country_code,
    country_name
from {{ ref('stg_shipping_details') }}

union all

select 'UNKNOWN' as country_code, 'Unknown (no default address)' as country_name
