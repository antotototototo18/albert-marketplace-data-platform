-- Drops unnamed_0: the export's row index.
-- Turns is_default from the strings '0'/'1' into a BOOL, so no one compares it to 1 as text.
-- Casts address_id to INT64.
-- A buyer has 1 to 3 addresses (33,219 / 33,561 / 33,220 buyers): this table fans
-- out any join on c_id. is_default is the rule that picks one (int_orders__country).
select
    cast(address_id as int64) as address_id,
    c_id,
    is_default = '1'          as is_default
from {{ source('bronze_legacy', 'customer_shipping') }}
