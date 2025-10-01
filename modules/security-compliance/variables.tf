variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "api_gateway_stage_arn" {
  description = "API Gateway stage ARN for WAF association"
  type        = string
}

variable "cloudtrail_bucket_name" {
  description = "S3 bucket name for CloudTrail logs"
  type        = string
}

variable "config_bucket_name" {
  description = "S3 bucket name for Config"
  type        = string
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
}