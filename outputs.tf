output "vpc_id" {
  description = "VPC ID"
  value       = module.networking.vpc_id
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.compute.ecs_cluster_name
}

output "api_gateway_url" {
  description = "API Gateway URL"
  value       = module.api.api_gateway_url
}

output "rds_endpoint" {
  description = "RDS endpoint"
  value       = module.database.rds_endpoint
  sensitive   = true
}

output "valkey_endpoint" {
  description = "Valkey endpoint"
  value       = module.cache.valkey_endpoint
  sensitive   = true
}

output "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  value       = module.auth.user_pool_id
}

output "cognito_user_pool_client_id" {
  description = "Cognito User Pool Client ID"
  value       = module.auth.user_pool_client_id
}

output "s3_logs_bucket" {
  description = "S3 logs bucket name"
  value       = module.storage.logs_bucket_name
}

output "s3_assets_bucket" {
  description = "S3 assets bucket name"
  value       = module.storage.assets_bucket_name
}

output "cognito_hosted_ui_url" {
  description = "Cognito Hosted UI URL for authentication"
  value       = module.auth.hosted_ui_url
}

output "cognito_domain" {
  description = "Cognito User Pool Domain"
  value       = module.auth.user_pool_domain
}