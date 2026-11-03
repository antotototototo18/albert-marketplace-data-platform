-- GRAIN: one row per product that has at least one review.
-- product_reviews is many-to-many with sales: up to 376 reviews for one product.
-- Joining it to order lines counts each line once per review (17x the units on the
-- course's own example). It is aggregated to the product HERE, before anything
-- joins it, so no join downstream can multiply a row.
-- review has no date: these are ratings as of the last load, not as of the sale.
select
    pr.p_id,
    count(*)                      as review_count,
    avg(r.rating)                 as avg_rating,
    countif(r.review_text is not null) as reviews_with_text
from {{ ref('stg_product_reviews') }} as pr
join {{ ref('stg_review') }} as r using (review_id)
group by pr.p_id
