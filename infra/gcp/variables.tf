variable "project_id" {
  description = "GCP project id"
  type        = string
  default     = "exec-kpi"
}

variable "region" {
  description = "Default region"
  type        = string
  default     = "us-central1"
}

variable "bq_dataset_id" {
  description = "BigQuery dataset for dbt / API / ML"
  type        = string
  default     = "execkpi_execkpi"
}

variable "bq_location" {
  description = "BigQuery dataset location"
  type        = string
  default     = "US"
}
