-- L07 quality-gate drill, 2026-11-06. Designed against one L05 test:
-- dbt_utils.unique_combination_of_columns(order_id, p_id) on stg_order_items.
-- The poison is a second copy of one real order line of 2026-09-16
-- (order 222935, product B019QY5QVS, qty 10). The next MERGE for that day updates
-- both copies and removes neither, so the duplicate survives the run.
-- Clean baseline for 2026-09-16 in gold: 1201 units, 364 lines, EUR 32,802.35.
-- If the bad row reaches the marts: 1211 units and 365 lines.

-- 1. Insert (run before the drill).
INSERT INTO `data-engineering-i1.group6_bronze.order_items_raw` (order_id, p_id, qty, price_at_purchase, _loaded_at)
SELECT order_id, p_id, qty, price_at_purchase, CURRENT_TIMESTAMP()
FROM `data-engineering-i1.group6_bronze.order_items_raw`
WHERE order_id = '222935' AND p_id = 'B019QY5QVS'
LIMIT 1;

-- 2. Remove (run after the drill): keep exactly one copy of the line.
-- DELETE FROM `data-engineering-i1.group6_bronze.order_items_raw`
-- WHERE order_id = '222935' AND p_id = 'B019QY5QVS';
-- then re-run the DAG for 2026-09-16: the MERGE inserts the line back once.
