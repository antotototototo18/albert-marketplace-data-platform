-- Tuning probe for orders: the slice Q2 reads from it.
SELECT order_id, buyer_id, order_date
FROM `${orders}`
WHERE order_date > DATE_SUB(DATE '2026-09-14', INTERVAL 28 DAY);
