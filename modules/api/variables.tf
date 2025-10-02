variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "lambda_execution_role_arn" {
  description = "Lambda execution role ARN"
  type        = string
}

variable "user_pool_id" {
  description = "Cognito User Pool ID"
  type        = string
}

variable "user_pool_client_id" {
  description = "Cognito User Pool Client ID"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID for VPC Links"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for VPC Links"
  type        = list(string)
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
}