output "artifacts_bucket" {
  value = aws_s3_bucket.execkpi_artifacts.bucket
}

output "iam_user" {
  value = aws_iam_user.execkpi_user.name
}
