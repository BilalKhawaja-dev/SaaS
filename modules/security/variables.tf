variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
}

variable "deployment_id" {
  description = "Unique deployment identifier"
  type        = string
  default     = ""
}