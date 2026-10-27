-- Bronze stays in the bucket. These definitions read the files on every query.
-- Legacy tables: one Parquet file per table, every column STRING (ADR-0002).
CREATE OR REPLACE EXTERNAL TABLE `data-engineering-i1.group6_bronze.orders`
OPTIONS (format = 'PARQUET', uris = ['gs://data-engineering-i1-group6/bronze/legacy/orders/*.parquet']);

CREATE OR REPLACE EXTERNAL TABLE `data-engineering-i1.group6_bronze.order_items`
OPTIONS (format = 'PARQUET', uris = ['gs://data-engineering-i1-group6/bronze/legacy/order_items/*.parquet']);

CREATE OR REPLACE EXTERNAL TABLE `data-engineering-i1.group6_bronze.product`
OPTIONS (format = 'PARQUET', uris = ['gs://data-engineering-i1-group6/bronze/legacy/product/*.parquet']);

CREATE OR REPLACE EXTERNAL TABLE `data-engineering-i1.group6_bronze.review`
OPTIONS (format = 'PARQUET', uris = ['gs://data-engineering-i1-group6/bronze/legacy/review/*.parquet']);

CREATE OR REPLACE EXTERNAL TABLE `data-engineering-i1.group6_bronze.product_reviews`
OPTIONS (format = 'PARQUET', uris = ['gs://data-engineering-i1-group6/bronze/legacy/product_reviews/*.parquet']);

CREATE OR REPLACE EXTERNAL TABLE `data-engineering-i1.group6_bronze.customer_shipping`
OPTIONS (format = 'PARQUET', uris = ['gs://data-engineering-i1-group6/bronze/legacy/customer_shipping/*.parquet']);

CREATE OR REPLACE EXTERNAL TABLE `data-engineering-i1.group6_bronze.shipping_details`
OPTIONS (format = 'PARQUET', uris = ['gs://data-engineering-i1-group6/bronze/legacy/shipping_details/*.parquet']);

-- Kept external on purpose: append-only events, read by L05 staging, not filtered
-- repeatedly yet. dt is the UTC day of event_time, taken from the object path.
CREATE OR REPLACE EXTERNAL TABLE `data-engineering-i1.group6_bronze.clickstream`
WITH PARTITION COLUMNS (dt DATE)
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://data-engineering-i1-group6/bronze/clickstream/v1/*'],
  hive_partition_uri_prefix = 'gs://data-engineering-i1-group6/bronze/clickstream/v1',
  require_hive_partition_filter = true
);
