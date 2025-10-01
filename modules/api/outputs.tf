output "api_gateway_url" {
  description = "API Gateway URL"
  value       = aws_api_gateway_deployment.main.invoke_url
}

output "api_gateway_id" {
  description = "API Gateway ID"
  value       = aws_api_gateway_rest_api.main.id
}

output "api_gateway_stage_arn" {
  description = "API Gateway stage ARN"
  value       = aws_api_gateway_deployment.main.execution_arn
}