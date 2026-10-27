-- Tuning probe for CLUSTER BY p_id: the full history of one product.
SELECT order_date, qty
FROM `${order_items}`
WHERE p_id = '${p_id}';
