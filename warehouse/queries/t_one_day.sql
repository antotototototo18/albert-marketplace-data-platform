-- Tuning probe for the partition grain: one day of order lines.
SELECT p_id, qty
FROM `${order_items}`
WHERE order_date = DATE '2026-09-14';
