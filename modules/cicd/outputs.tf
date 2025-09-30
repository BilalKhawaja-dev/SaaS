output "terraform_state_bucket" {
  description = "Terraform state S3 bucket name"
  value       = aws_s3_bucket.terraform_state.bucket
}

output "terraform_locks_table" {
  description = "Terraform locks DynamoDB table name"
  value       = aws_dynamodb_table.terraform_locks.name
}

output "codebuild_project_name" {
  description = "CodeBuild project name"
  value       = aws_codebuild_project.terraform.name
}