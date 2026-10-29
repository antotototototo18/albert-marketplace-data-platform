-- How many order lines one row of each candidate grain summarises.
-- A ratio near 1 means a materialised view at that grain stores almost the table again.
SELECT
  COUNT(*) AS order_lines,
  COUNT(DISTINCT FORMAT('%s|%t', p_id, order_date)) AS product_day,
  COUNT(DISTINCT FORMAT('%s|%t', p_id, DATE_TRUNC(order_date, WEEK(MONDAY)))) AS product_week,
  COUNT(DISTINCT FORMAT('%s|%t', p_id, DATE_TRUNC(order_date, MONTH))) AS product_month,
  COUNT(DISTINCT p_id) AS product
FROM `${order_items}`;
