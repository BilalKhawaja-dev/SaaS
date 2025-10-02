output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "ecs_cluster_id" {
  description = "ECS cluster ID"
  value       = aws_ecs_cluster.main.id
}

output "frontend_service_name" {
  description = "Frontend ECS service name"
  value       = aws_ecs_service.frontend.name
}

output "subscription_service_name" {
  description = "Subscription ECS service name"
  value       = aws_ecs_service.subscription_service.name
}

output "support_service_name" {
  description = "Support ECS service name"
  value       = aws_ecs_service.support_service.name
}