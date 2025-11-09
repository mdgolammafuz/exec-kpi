terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

# 1) S3 bucket for ML artifacts
resource "aws_s3_bucket" "execkpi_artifacts" {
  bucket = var.artifacts_bucket_name

  tags = {
    app = "execkpi"
  }
}

# 2) IAM user for the app / CI
resource "aws_iam_user" "execkpi_user" {
  name = "execkpi-user"
}

# 3) Policy: allow put/get on that bucket
data "aws_iam_policy_document" "execkpi_artifacts_rw" {
  statement {
    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:ListBucket"
    ]
    resources = [
      aws_s3_bucket.execkpi_artifacts.arn,
      "${aws_s3_bucket.execkpi_artifacts.arn}/*"
    ]
  }
}

resource "aws_iam_policy" "execkpi_artifacts_rw" {
  name   = "execkpi-artifacts-rw"
  policy = data.aws_iam_policy_document.execkpi_artifacts_rw.json
}

# attach policy to user
resource "aws_iam_user_policy_attachment" "execkpi_user_attach" {
  user       = aws_iam_user.execkpi_user.name
  policy_arn = aws_iam_policy.execkpi_artifacts_rw.arn
}
