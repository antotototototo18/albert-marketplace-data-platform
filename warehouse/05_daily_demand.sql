-- Daily demand per product, for the ML team. Partitioned and clustered like its
-- base table so that a date window or a product prunes the view as well.
-- Collapse ratio and the decision to keep it: docs/warehouse-tuning.md.
CREATE OR REPLACE MATERIALIZED VIEW `data-engineering-i1.group6_warehouse.daily_demand`
PARTITION BY DATE_TRUNC(order_date, MONTH)
CLUSTER BY p_id
AS
SELECT
  p_id,
  order_date,
  SUM(qty) AS units,
  SUM(qty * price_at_purchase) AS revenue,
  COUNT(*) AS order_lines
FROM `data-engineering-i1.group6_warehouse.order_items`
GROUP BY p_id, order_date;
