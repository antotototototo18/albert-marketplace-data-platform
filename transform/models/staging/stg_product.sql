-- Drops unnamed_0: the export's row index.
-- Turns the 6 empty product names into NULL, after trimming (none is padded today).
-- Casts price to BIGNUMERIC: up to 20 decimals in the source, NUMERIC would round them.
-- Casts qty and category_id to INT64. Keeps p_id as STRING: 6 ids start with 0.
-- Leaves p_desc as the serialised JSON it is: gold does not read it.
select
    p_id,
    nullif(trim(p_name), '')     as p_name,
    p_desc,
    cast(price as bignumeric)    as catalogue_price,
    cast(qty as int64)           as stock_qty,
    cast(category_id as int64)   as category_id
from {{ source('bronze_legacy', 'product') }}
