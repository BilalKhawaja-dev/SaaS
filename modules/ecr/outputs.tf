output "frontend_repository_url" {
  description = "URL of the frontend ECR repository"
  value       = aws_ecr_repository.frontend.repository_url
}

output "subscription_service_repository_url" {
  description = "URL of the subscription service ECR repository"
  value       = aws_ecr_repository.subscription_service.repository_url
}

output "support_service_repository_url" {
  description = "URL of the support service ECR repository"
  value       = aws_ecr_repository.support_service.repository_url
}

output "frontend_repository_name" {
  description = "Name of the frontend ECR repository"
  value       = aws_ecr_repository.frontend.name
}

output "subscription_service_repository_name" {
  description = "Name of the subscription service ECR repository"
  value       = aws_ecr_repository.subscription_service.name
}

output "support_service_repository_name" {
  description = "Name of the support service ECR repository"
  value       = aws_ecr_repository.support_service.name
}