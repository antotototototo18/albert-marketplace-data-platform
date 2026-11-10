-- Q1 (finance, flow A7): revenue and orders per month, last twelve months.
-- "Today" is the last order date in the export, so every run gives the same window.
SELECT
  DATE_TRUNC(order_date, MONTH) AS month,
  COUNT(DISTINCT order_id) AS orders,
  ROUND(SUM(qty * price_at_purchase), 2) AS revenue
FROM `${order_items}`
WHERE order_date > DATE_SUB(DATE '2026-09-14', INTERVAL 12 MONTH)
  AND order_date <= DATE '2026-09-14'
GROUP BY month
ORDER BY month;
