-- Monthly demand: keep the DATE partition key visible to BigQuery.
-- Inclusive start, exclusive end; includes every day of the requested month.
SELECT p_id, order_date, SUM(qty) AS units
FROM `data-engineering-i1.group6_gold.fct_order_items`
WHERE order_date >= DATE '${month_start}' AND order_date < DATE '${month_end}'
GROUP BY p_id, order_date
ORDER BY p_id, order_date;
