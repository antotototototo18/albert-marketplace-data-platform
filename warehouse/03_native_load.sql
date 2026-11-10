-- The working set, copied out of bronze into native storage: the baseline every
-- tuned number is compared to. Columns are typed where a query filters, joins or
-- sums on them; nothing is cleaned, deduplicated or dropped (that is L05).
-- Identifiers that can start with 0 stay STRING: p_id, zip, phone (data dictionary).
-- product, customer_shipping and shipping_details are not tuned (docs/warehouse-tuning.md),
-- so they are loaded once under their final name.
CREATE OR REPLACE TABLE `data-engineering-i1.group6_warehouse.orders_untuned` AS
SELECT
  unnamed_0,
  CAST(order_id AS INT64) AS order_id,
  buyer_id,
  discount_id,
  CAST(payment_id AS INT64) AS payment_id,
  CAST(order_date AS DATE) AS order_date
FROM `data-engineering-i1.group6_bronze.orders`;

-- order_items has no date of its own. It takes the order's date so that it can be
-- partitioned: one order has one date, so the join cannot multiply rows.
CREATE OR REPLACE TABLE `data-engineering-i1.group6_warehouse.order_items_untuned` AS
SELECT
  CAST(i.order_id AS INT64) AS order_id,
  i.p_id,
  CAST(i.qty AS INT64) AS qty,
  CAST(i.price_at_purchase AS NUMERIC) AS price_at_purchase,
  o.order_date
FROM `data-engineering-i1.group6_bronze.order_items` AS i
JOIN `data-engineering-i1.group6_warehouse.orders_untuned` AS o
  ON o.order_id = CAST(i.order_id AS INT64);

-- price has up to 20 decimals in the source: BIGNUMERIC keeps them, NUMERIC would not.
CREATE OR REPLACE TABLE `data-engineering-i1.group6_warehouse.product` AS
SELECT
  unnamed_0,
  p_id,
  p_name,
  p_desc,
  CAST(price AS BIGNUMERIC) AS price,
  CAST(qty AS INT64) AS qty,
  CAST(category_id AS INT64) AS category_id
FROM `data-engineering-i1.group6_bronze.product`;

CREATE OR REPLACE TABLE `data-engineering-i1.group6_warehouse.review_untuned` AS
SELECT
  unnamed_0,
  CAST(review_id AS INT64) AS review_id,
  buyer_id,
  r_desc,
  title,
  CAST(rating AS INT64) AS rating,
  seller_product_flag
FROM `data-engineering-i1.group6_bronze.review`;

CREATE OR REPLACE TABLE `data-engineering-i1.group6_warehouse.product_reviews_untuned` AS
SELECT unnamed_0, p_id, CAST(review_id AS INT64) AS review_id
FROM `data-engineering-i1.group6_bronze.product_reviews`;

CREATE OR REPLACE TABLE `data-engineering-i1.group6_warehouse.customer_shipping` AS
SELECT
  unnamed_0,
  CAST(address_id AS INT64) AS address_id,
  c_id,
  CAST(is_default AS INT64) AS is_default
FROM `data-engineering-i1.group6_bronze.customer_shipping`;

CREATE OR REPLACE TABLE `data-engineering-i1.group6_warehouse.shipping_details` AS
SELECT
  unnamed_0,
  CAST(address_id AS INT64) AS address_id,
  street_address,
  city,
  state,
  zip,
  country,
  phone
FROM `data-engineering-i1.group6_bronze.shipping_details`;
