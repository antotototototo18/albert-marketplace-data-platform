# Adoption baseline from L02-L07; reconcile metadata with live inventory before apply.
resource "google_storage_bucket" "bronze" {
  name                        = "data-engineering-i1-group6"
  location                    = "EUROPE-WEST1"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  soft_delete_policy {
    retention_duration_seconds = 604800
  }

  dynamic "lifecycle_rule" {
    for_each = jsondecode(file("${path.module}/../lifecycle.json")).rule
    content {
      action {
        type          = lifecycle_rule.value.action.type
        storage_class = lifecycle_rule.value.action.storageClass
      }
      condition {
        age                   = lifecycle_rule.value.condition.age
        matches_prefix        = lifecycle_rule.value.condition.matchesPrefix
        matches_storage_class = lifecycle_rule.value.condition.matchesStorageClass
      }
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_bigquery_dataset" "bronze" {
  dataset_id                 = "group6_bronze"
  location                   = "europe-west1"
  description                = "External tables over gs://data-engineering-i1-group6/bronze. Definitions only, no stored rows."
  delete_contents_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_bigquery_dataset" "warehouse" {
  dataset_id                 = "group6_warehouse"
  location                   = "europe-west1"
  description                = "Native tables loaded from group6_bronze (L04). Typed, not cleaned."
  delete_contents_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_bigquery_dataset" "silver" {
  dataset_id                 = "group6_silver"
  location                   = "europe-west1"
  description                = ""
  delete_contents_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_bigquery_dataset" "gold" {
  dataset_id                 = "group6_gold"
  location                   = "europe-west1"
  description                = ""
  delete_contents_on_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}
