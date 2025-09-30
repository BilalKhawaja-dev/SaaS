variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "api_gateway_domain" {
  description = "API Gateway domain for OAuth callbacks"
  type        = string
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
}