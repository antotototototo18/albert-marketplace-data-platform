-- Replace the export table with the actual billing view supplied by the teacher.
-- Standard export schema; @start_date and @end_date are DATE, end exclusive.
-- Correlated subqueries avoid multiplying costs by labels or credits.
SELECT
  DATE(usage_start_time) AS day,
  service.description AS service,
  sku.id AS sku_id,
  sku.description AS sku,
  currency,
  COALESCE((SELECT value FROM UNNEST(labels) WHERE key = 'team' LIMIT 1),
           'unattributed') AS team,
  SUM(cost) AS gross_cost,
  SUM(cost + IFNULL((SELECT SUM(amount) FROM UNNEST(credits)), 0)) AS net_cost
FROM `${billing_export}`
WHERE project.id = 'data-engineering-i1'
  AND usage_start_time >= TIMESTAMP(@start_date)
  AND usage_start_time < TIMESTAMP(@end_date)
GROUP BY day, service, sku_id, sku, currency, team
ORDER BY day, net_cost DESC;
