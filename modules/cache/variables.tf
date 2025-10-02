variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for multi-AZ deployment"
  type        = list(string)
}

variable "elasticache_security_group_id" {
  description = "ElastiCache security group ID"
  type        = string
}

variable "elasticache_node_type" {
  description = "ElastiCache node type"
  type        = string
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
}