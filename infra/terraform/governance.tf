# L10: classify columns, then grant on the class (docs/governance.md, ADR-0010).
#
# The taxonomy only enforces anything because FINE_GRAINED_ACCESS_CONTROL is
# activated: without it the tags are a filing scheme that protects nothing.
# Tags are attached to columns by scripts/apply_policy_tags.py, because the
# tables are created by SQL (warehouse/03_native_load.sql), not by Terraform.
#
# Treat this file as privileged: destroying the taxonomy silently unprotects every
# tagged column, and the table schemas keep showing the tag afterwards.
# Data Catalog taxonomies have no labels field; attribution stays on the datasets.

resource "google_data_catalog_taxonomy" "pii" {
  region                 = "europe-west1"
  display_name           = "group6-marketplace-pii"
  description            = "Group 6 personal-data classes. Grant access on a tag, never on a table."
  activated_policy_types = ["FINE_GRAINED_ACCESS_CONTROL"]

  lifecycle {
    prevent_destroy = true
  }
}

# Named for what the data is, never for who may see it.
resource "google_data_catalog_policy_tag" "pii_contact" {
  taxonomy     = google_data_catalog_taxonomy.pii.id
  display_name = "pii-contact"
  description  = "Names or reaches a person: street address, phone, email, full name."
}

resource "google_data_catalog_policy_tag" "pii_location_coarse" {
  taxonomy     = google_data_catalog_taxonomy.pii.id
  display_name = "pii-location-coarse"
  description  = "Location finer than a region: city, postcode. A quasi-identifier."
}

# Second key for pii-contact. Empty by default: no model or report needs these
# columns. Add a member only for an open GDPR request (issue), remove it on close.
variable "pii_contact_readers" {
  description = "Members (user:... ) allowed to read pii-contact columns, for the duration of a GDPR request."
  type        = set(string)
  default     = []
}

resource "google_data_catalog_policy_tag_iam_member" "pii_contact_reader" {
  for_each   = var.pii_contact_readers
  policy_tag = google_data_catalog_policy_tag.pii_contact.name
  role       = "roles/datacatalog.categoryFineGrainedReader"
  member     = each.value
}

output "policy_tags" {
  description = "Resource names written into column schemas by scripts/apply_policy_tags.py."
  value = {
    pii_contact         = google_data_catalog_policy_tag.pii_contact.name
    pii_location_coarse = google_data_catalog_policy_tag.pii_location_coarse.name
  }
}
