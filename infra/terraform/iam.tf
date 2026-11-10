# Preserve resource-level grants already present in the shared remote state.
# These are the human identities used by the existing pipeline; no project IAM.
# IAM members have no labels field and no direct charge; attribute via their dataset.
locals {
  dataset_writers = {
    bronze_arabeau      = { dataset = google_bigquery_dataset.bronze.dataset_id, member = "user:arabeau@albertschool.com" }
    bronze_csibieude    = { dataset = google_bigquery_dataset.bronze.dataset_id, member = "user:csibieude@albertschool.com" }
    warehouse_arabeau   = { dataset = google_bigquery_dataset.warehouse.dataset_id, member = "user:arabeau@albertschool.com" }
    warehouse_csibieude = { dataset = google_bigquery_dataset.warehouse.dataset_id, member = "user:csibieude@albertschool.com" }
  }
}

resource "google_bigquery_dataset_iam_member" "writer" {
  for_each   = local.dataset_writers
  dataset_id = each.value.dataset
  role       = "roles/bigquery.dataEditor"
  member     = each.value.member
}

resource "google_bigquery_dataset_iam_member" "bronze_reader_arabeau" {
  dataset_id = google_bigquery_dataset.bronze.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "user:arabeau@albertschool.com"
}
