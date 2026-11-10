-- The tuned tables, under the names consumers query. Each layout is measured
-- against its *_untuned copy in docs/warehouse-tuning.md.

-- Month grain: 37 partitions over three years. Day grain builds 1,096 partitions
-- of about 16 kB each (measured below with order_items_day).
CREATE OR REPLACE TABLE `data-engineering-i1.group6_warehouse.orders`
PARTITION BY DATE_TRUNC(order_date, MONTH) AS
SELECT * FROM `data-engineering-i1.group6_warehouse.orders_untuned`;

CREATE OR REPLACE TABLE `data-engineering-i1.group6_warehouse.order_items`
PARTITION BY DATE_TRUNC(order_date, MONTH)
CLUSTER BY p_id AS
SELECT * FROM `data-engineering-i1.group6_warehouse.order_items_untuned`;

-- Experiment only: the same table at day grain, to measure what the finer grain buys.
CREATE OR REPLACE TABLE `data-engineering-i1.group6_warehouse.order_items_day`
PARTITION BY order_date
CLUSTER BY p_id AS
SELECT * FROM `data-engineering-i1.group6_warehouse.order_items_untuned`;

-- No date to partition by. Clustering is tried on the column each table is
-- filtered by; whether it pays depends on the question (docs/warehouse-tuning.md).
CREATE OR REPLACE TABLE `data-engineering-i1.group6_warehouse.review`
CLUSTER BY rating AS
SELECT * FROM `data-engineering-i1.group6_warehouse.review_untuned`;

CREATE OR REPLACE TABLE `data-engineering-i1.group6_warehouse.product_reviews`
CLUSTER BY p_id AS
SELECT * FROM `data-engineering-i1.group6_warehouse.product_reviews_untuned`;
