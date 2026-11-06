-- L07, 2026-11-06: put bronze back to its legacy state before the measured back-fill.
--
-- Why: a back-fill of 2026-09-15..16 was started from the Airflow UI at 12:21 UTC
-- (origin not confirmed) before any prediction was written. The step asks for the
-- prediction first, so that run does not count; its rows are removed here and the
-- back-fill is redone after the prediction in docs/orchestration.md.
--
-- What is removed: only rows the DAG inserted. Legacy rows carry the CSV row index
-- (unnamed_0); DAG rows do not. Every removed row can be re-extracted from the
-- source database. One transaction: lines first, then their orders, so a failure
-- cannot leave lines without their order.
--
-- Not reverted: the 402 legacy orders of 2026-09-14 (and their lines) that the
-- 12:56 UTC run merged again keep a 2026-11-06 _loaded_at, and their empty
-- discount_id became NULL. Neither column is read downstream (stg_orders drops
-- discount_id).

BEGIN TRANSACTION;

DELETE FROM `data-engineering-i1.group6_bronze.order_items_raw`
WHERE order_id IN (
  SELECT order_id FROM `data-engineering-i1.group6_bronze.orders_raw` WHERE unnamed_0 IS NULL
);

DELETE FROM `data-engineering-i1.group6_bronze.orders_raw`
WHERE unnamed_0 IS NULL;

COMMIT TRANSACTION;
