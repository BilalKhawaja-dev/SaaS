output "app_log_group_name" {
  description = "Application log group name"
  value       = aws_cloudwatch_log_group.app_logs.name
}

output "api_log_group_name" {
  description = "API log group name"
  value       = aws_cloudwatch_log_group.api_logs.name
}

output "dashboard_url" {
  description = "CloudWatch Dashboard URL"
  value       = "https://console.aws.amazon.com/cloudwatch/home?region=eu-west-2#dashboards:name=${aws_cloudwatch_dashboard.enterprise.dashboard_name}"
}