# Both resources were made by hand in lessons 2 and 4 and hold real data, so
# prevent_destroy turns any plan that would delete them into an error.

resource "google_storage_bucket" "bronze" {
  name                        = "${var.project_id}-${var.group}"
  location                    = "EUROPE-WEST1"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  force_destroy               = false

  labels = {
    owner = "antoine-rabeau"
  }

  lifecycle_rule {
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
    condition {
      age            = 30
      matches_prefix = ["bronze/"]
    }
  }

  lifecycle_rule {
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
    condition {
      age            = 90
      matches_prefix = ["bronze/"]
    }
  }

  lifecycle_rule {
    action {
      type          = "SetStorageClass"
      storage_class = "ARCHIVE"
    }
    condition {
      age            = 365
      matches_prefix = ["bronze/"]
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_bigquery_dataset" "warehouse" {
  dataset_id = "l04_rabeau"
  location   = "europe-west1"

  lifecycle {
    prevent_destroy = true
  }
}
