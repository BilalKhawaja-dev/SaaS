output "logs_bucket_name" {
  description = "Name of the logs S3 bucket"
  value       = aws_s3_bucket.logs.bucket
}

output "assets_bucket_name" {
  description = "Name of the assets S3 bucket"
  value       = aws_s3_bucket.assets.bucket
}

output "analytics_bucket_name" {
  description = "Name of the analytics S3 bucket"
  value       = aws_s3_bucket.analytics.bucket
}

output "athena_workgroup_name" {
  description = "Athena workgroup name"
  value       = aws_athena_workgroup.main.name
}

output "athena_database_name" {
  description = "Athena database name"
  value       = aws_athena_database.main.name
}