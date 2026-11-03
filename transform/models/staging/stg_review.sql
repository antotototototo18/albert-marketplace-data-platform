-- Drops unnamed_0: the export's row index.
-- Trims blank review text into NULL: 14 empty strings, 110 single spaces.
-- Trims the 6 review texts and 10 titles that carry leading or trailing spaces.
-- Drops seller_product_flag: 'S' on all 111,322 rows, an undocumented code.
-- Casts review_id and rating to INT64.
select
    cast(review_id as int64)   as review_id,
    buyer_id,
    nullif(trim(r_desc), '')   as review_text,
    nullif(trim(title), '')    as review_title,
    cast(rating as int64)      as rating
from {{ source('bronze_legacy', 'review') }}
