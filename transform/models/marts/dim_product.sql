-- GRAIN: one row per product in the catalogue.
-- Ratings come pre-aggregated from int_product__ratings (one row per product), so
-- this join cannot multiply a product. Products with no review get 0 and NULL.
select
    p.p_id,
    p.p_name,
    p.category_id,
    p.catalogue_price,
    coalesce(r.review_count, 0)  as review_count,
    r.avg_rating
from {{ ref('stg_product') }} as p
left join {{ ref('int_product__ratings') }} as r using (p_id)
