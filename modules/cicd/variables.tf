variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "source_bucket_name" {
  description = "S3 bucket name for source code"
  type        = string
}

variable "artifacts_bucket_name" {
  description = "S3 bucket name for build artifacts"
  type        = string
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
}