import {
  to = google_storage_bucket.bronze
  id = "data-engineering-i1/data-engineering-i1-group6"
}

import {
  to = google_bigquery_dataset.bronze
  id = "projects/data-engineering-i1/datasets/group6_bronze"
}

import {
  to = google_bigquery_dataset.warehouse
  id = "projects/data-engineering-i1/datasets/group6_warehouse"
}

import {
  to = google_bigquery_dataset.silver
  id = "projects/data-engineering-i1/datasets/group6_silver"
}

import {
  to = google_bigquery_dataset.gold
  id = "projects/data-engineering-i1/datasets/group6_gold"
}

# The L08 import blocks of the dataEditor members were removed in L10: those grants
# were narrowed to dataViewer (iam.tf) and are no longer in the configuration.
