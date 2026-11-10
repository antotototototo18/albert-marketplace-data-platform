-- Fallback when no billing export is accessible. Units, not an invoice.
-- Set @start_date and @end_date (DATE), end exclusive; no artificial zero days.
SELECT
  DATE(creation_time) AS day,
  COUNT(*) AS jobs,
  SUM(IFNULL(total_bytes_processed, 0)) AS bytes_processed,
  SUM(IFNULL(total_bytes_billed, 0)) AS bytes_billed,
  COUNTIF(cache_hit) AS cache_hits
FROM `data-engineering-i1.region-europe-west1.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
WHERE creation_time >= TIMESTAMP(@start_date)
  AND creation_time < TIMESTAMP(@end_date)
  AND job_type = 'QUERY' AND state = 'DONE'
  AND statement_type != 'SCRIPT' AND error_result IS NULL
  AND (
    EXISTS (
      SELECT 1 FROM UNNEST(referenced_tables) AS t
      WHERE t.project_id = 'data-engineering-i1'
        AND STARTS_WITH(t.dataset_id, 'group6_')
    )
    OR EXISTS (
      SELECT 1 FROM UNNEST(labels) AS l WHERE l.key = 'team' AND l.value = 'group6'
    )
  )
GROUP BY day
ORDER BY day;
