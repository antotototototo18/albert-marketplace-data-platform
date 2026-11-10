terraform {
  required_version = "= 1.13.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "= 8.10.0"
    }
  }

  backend "gcs" {
    bucket = "data-engineering-i1-group6-tfstate"
    prefix = "platform"
  }
}

provider "google" {
  project = "data-engineering-i1"
  region  = "europe-west1"
}
