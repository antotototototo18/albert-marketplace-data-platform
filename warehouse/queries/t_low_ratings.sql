-- Tuning probe for review CLUSTER BY rating: the 1 and 2 star reviews to triage.
SELECT review_id, title, r_desc
FROM `${review}`
WHERE rating <= 2;
