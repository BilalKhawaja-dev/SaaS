variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "notification_email" {
  description = "Email address for notifications"
  type        = string
}

variable "db_instance_id" {
  description = "RDS instance identifier"
  type        = string
}

variable "ecs_service_name" {
  description = "ECS service name"
  type        = string
}

variable "ecs_cluster_name" {
  description = "ECS cluster name"
  type        = string
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
}