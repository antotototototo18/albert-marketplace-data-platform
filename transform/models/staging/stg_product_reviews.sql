-- Drops unnamed_0: the export's row index.
-- Casts review_id to INT64 so it joins stg_review without a cast downstream.
-- This is a many-to-many bridge (up to 376 reviews for one product): nothing
-- may join it to order lines before int_product__ratings aggregates it.
select
    p_id,
    cast(review_id as int64) as review_id
from {{ source('bronze_legacy', 'product_reviews') }}
