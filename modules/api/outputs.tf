output "api_gateway_url" {
  description = "API Gateway URL"
  value       = aws_api_gateway_stage.dev.invoke_url
}

output "api_gateway_id" {
  description = "API Gateway ID"
  value       = aws_api_gateway_rest_api.main.id
}

output "api_gateway_stage_arn" {
  description = "API Gateway stage ARN"
  value       = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

output "nlb_target_group_frontend_arn" {
  description = "NLB target group ARN for frontend service"
  value       = aws_lb_target_group.frontend.arn
}

output "nlb_target_group_subscription_arn" {
  description = "NLB target group ARN for subscription service"
  value       = aws_lb_target_group.subscription.arn
}

output "nlb_target_group_support_arn" {
  description = "NLB target group ARN for support service"
  value       = aws_lb_target_group.support.arn
}