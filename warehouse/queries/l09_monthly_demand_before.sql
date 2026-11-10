-- L09 baseline: the regex hides the monthly partition key from pruning.
-- month_start is an ISO date, always the first day of the requested month.
SELECT p_id, order_date, SUM(qty) AS units
FROM `data-engineering-i1.group6_gold.fct_order_items`
WHERE REGEXP_CONTAINS(CAST(order_date AS STRING), r'^${month}-')
GROUP BY p_id, order_date
ORDER BY p_id, order_date;
