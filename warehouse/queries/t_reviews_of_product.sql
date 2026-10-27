-- Tuning probe for product_reviews CLUSTER BY p_id: the reviews of one product.
SELECT review_id
FROM `${product_reviews}`
WHERE p_id = '${p_id}';
