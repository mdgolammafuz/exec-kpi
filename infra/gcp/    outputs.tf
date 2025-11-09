output "dataset_id" {
  value = google_bigquery_dataset.execkpi.dataset_id
}

output "service_account_email" {
  value = google_service_account.execkpi_sa.email
}
