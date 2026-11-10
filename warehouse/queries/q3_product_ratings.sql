-- Q3 (catalogue, input of L05 reviews): average rating of products with more than
-- fifty reviews. review records no product; product_reviews says which product.
SELECT
  pr.p_id,
  COUNT(*) AS reviews,
  ROUND(AVG(r.rating), 2) AS avg_rating
FROM `${review}` AS r
JOIN `${product_reviews}` AS pr
  ON pr.review_id = r.review_id
GROUP BY pr.p_id
HAVING COUNT(*) > 50
ORDER BY reviews DESC;
