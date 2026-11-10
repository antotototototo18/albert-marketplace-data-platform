-- Daily demand per product over the last 28 days, read from the order lines.
SELECT p_id, order_date, SUM(qty) AS units
FROM `${order_items}`
WHERE order_date > DATE_SUB(DATE '2026-09-14', INTERVAL 28 DAY)
GROUP BY p_id, order_date;
