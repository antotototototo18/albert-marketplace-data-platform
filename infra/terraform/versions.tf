terraform {
  required_version = ">= 1.9"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 8.4"
    }
  }

  # Made by hand with gcloud: the state bucket cannot make itself. A backend
  # block takes no variables, so the name is a literal.
  backend "gcs" {
    bucket = "data-engineering-i1-rabeau-antoine-tfstate"
    prefix = "infra"
  }
}
