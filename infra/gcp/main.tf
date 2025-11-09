terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# existing dataset (we imported it), so we match its settings
resource "google_bigquery_dataset" "execkpi" {
  dataset_id = var.bq_dataset_id
  location   = var.bq_location

  # keep the 60-day defaults that were already on the dataset
  default_table_expiration_ms     = 5184000000
  default_partition_expiration_ms = 5184000000

  delete_contents_on_destroy = true

  labels = {
    app = "execkpi"
  }
}

# service account for the project
resource "google_service_account" "execkpi_sa" {
  account_id   = "execkpi-sa"
  display_name = "ExecKPI Service Account"
}

# give it BigQuery admin (simple for demo)
resource "google_project_iam_member" "execkpi_bq_admin" {
  project = var.project_id
  role    = "roles/bigquery.admin"
  member  = "serviceAccount:${google_service_account.execkpi_sa.email}"
}
