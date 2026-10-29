-- Two datasets, both in the bucket's region: a query cannot join across regions,
-- and a dataset's location cannot be changed after creation.
CREATE SCHEMA IF NOT EXISTS `data-engineering-i1.group6_bronze`
OPTIONS (
  location = 'europe-west1',
  description = 'External tables over gs://data-engineering-i1-group6/bronze. Definitions only, no stored rows.'
);

CREATE SCHEMA IF NOT EXISTS `data-engineering-i1.group6_warehouse`
OPTIONS (
  location = 'europe-west1',
  description = 'Native tables loaded from group6_bronze (L04). Typed, not cleaned.'
);
