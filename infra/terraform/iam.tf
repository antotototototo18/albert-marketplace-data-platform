# Resource-level grants on the group's datasets. No project IAM: it belongs to the
# teaching team. IAM members have no labels field and no direct charge; attribute
# via their dataset.
#
# L10 narrowed these grants from roles/bigquery.dataEditor to dataViewer. The job
# history (docs/evidence/l10/08-who-writes.txt) shows that, since 2026-10-08, every
# write to group6_bronze and group6_warehouse came from the member who runs the L04
# loads and the L07 DAG; these two members only read (dbt sources, checks). Writes
# of the transformation layer go to group6_silver and group6_gold, which they own.
locals {
  dataset_readers = {
    bronze_arabeau      = { dataset = google_bigquery_dataset.bronze.dataset_id, member = "user:arabeau@albertschool.com" }
    bronze_csibieude    = { dataset = google_bigquery_dataset.bronze.dataset_id, member = "user:csibieude@albertschool.com" }
    warehouse_arabeau   = { dataset = google_bigquery_dataset.warehouse.dataset_id, member = "user:arabeau@albertschool.com" }
    warehouse_csibieude = { dataset = google_bigquery_dataset.warehouse.dataset_id, member = "user:csibieude@albertschool.com" }
  }
}

resource "google_bigquery_dataset_iam_member" "reader" {
  for_each   = local.dataset_readers
  dataset_id = each.value.dataset
  role       = "roles/bigquery.dataViewer"
  member     = each.value.member
}

# The bronze read grant already existed on its own since L03; keep it, under the
# new address, instead of deleting and recreating it.
moved {
  from = google_bigquery_dataset_iam_member.bronze_reader_arabeau
  to   = google_bigquery_dataset_iam_member.reader["bronze_arabeau"]
}
