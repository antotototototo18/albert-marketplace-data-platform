-- The same answer, read from the materialised view.
SELECT p_id, order_date, units
FROM `${daily_demand}`
WHERE order_date > DATE_SUB(DATE '2026-09-14', INTERVAL 28 DAY);
