-- L07: the two bronze tables the scheduler writes into. An external table cannot
-- be merged into, and a poison row cannot be inserted into one, so orders and
-- order_items get native copies; the five dimensions stay external (legacy only).
-- Columns stay STRING like the rest of bronze (ADR-0002): typing is staging's job.
-- _loaded_at says when a row last arrived; dbt source freshness reads it.
-- Re-runnable: the tables are created once and the legacy rows are merged on the
-- same keys the DAG uses (ADR-0007), so a second run inserts nothing.

CREATE TABLE IF NOT EXISTS `data-engineering-i1.group6_bronze.orders_raw` (
  order_id STRING NOT NULL,
  buyer_id STRING,
  discount_id STRING,
  payment_id STRING,
  order_date STRING,
  unnamed_0 STRING OPTIONS (description = 'Row index of the legacy CSV export; NULL for rows extracted by the DAG.'),
  _loaded_at TIMESTAMP NOT NULL
)
OPTIONS (description = 'Orders, merged on order_id by the L07 DAG. Legacy export plus scheduled extracts.');

CREATE TABLE IF NOT EXISTS `data-engineering-i1.group6_bronze.order_items_raw` (
  order_id STRING NOT NULL,
  p_id STRING NOT NULL,
  qty STRING,
  price_at_purchase STRING,
  _loaded_at TIMESTAMP NOT NULL
)
OPTIONS (description = 'Order lines, merged on (order_id, p_id) by the L07 DAG. Legacy export plus scheduled extracts.');

-- Labels so that L09 can attribute their storage and query cost: these tables are
-- created by SQL, not by Terraform, so nothing else will label them. Provisional
-- keys until L09 fixes the group's convention; SET OPTIONS is safe to re-run.
ALTER TABLE `data-engineering-i1.group6_bronze.orders_raw`
SET OPTIONS (labels = [('team', 'group6'), ('layer', 'bronze'), ('pipeline', 'marketplace-daily'), ('managed-by', 'sql')]);

ALTER TABLE `data-engineering-i1.group6_bronze.order_items_raw`
SET OPTIONS (labels = [('team', 'group6'), ('layer', 'bronze'), ('pipeline', 'marketplace-daily'), ('managed-by', 'sql')]);

-- The landing date of the legacy export is only in the object path.
MERGE `data-engineering-i1.group6_bronze.orders_raw` AS t
USING (
  SELECT
    order_id, buyer_id, discount_id, payment_id, order_date, unnamed_0,
    TIMESTAMP(PARSE_DATE('%Y-%m-%d', REGEXP_EXTRACT(_FILE_NAME, r'ingested_date=(\d{4}-\d{2}-\d{2})'))) AS _loaded_at
  FROM `data-engineering-i1.group6_bronze.orders`
) AS s
ON t.order_id = s.order_id
WHEN NOT MATCHED THEN INSERT ROW;

MERGE `data-engineering-i1.group6_bronze.order_items_raw` AS t
USING (
  SELECT
    order_id, p_id, qty, price_at_purchase,
    TIMESTAMP(PARSE_DATE('%Y-%m-%d', REGEXP_EXTRACT(_FILE_NAME, r'ingested_date=(\d{4}-\d{2}-\d{2})'))) AS _loaded_at
  FROM `data-engineering-i1.group6_bronze.order_items`
) AS s
ON t.order_id = s.order_id AND t.p_id = s.p_id
WHEN NOT MATCHED THEN INSERT ROW;
