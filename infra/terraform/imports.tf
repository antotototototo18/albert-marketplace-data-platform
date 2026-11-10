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

import {
  for_each = local.dataset_writers
  to       = google_bigquery_dataset_iam_member.writer[each.key]
  id       = "projects/data-engineering-i1/datasets/${each.value.dataset} roles/bigquery.dataEditor ${each.value.member}"
}

import {
  to = google_bigquery_dataset_iam_member.bronze_reader_arabeau
  id = "projects/data-engineering-i1/datasets/group6_bronze roles/bigquery.dataViewer user:arabeau@albertschool.com"
}
