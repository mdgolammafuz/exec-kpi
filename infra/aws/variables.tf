variable "region" {
  type    = string
  default = "us-east-1"  # free-tier friendly
}

variable "artifacts_bucket_name" {
  type    = string
  default = "execkpi-artifacts-demo"  # must be globally unique
}
