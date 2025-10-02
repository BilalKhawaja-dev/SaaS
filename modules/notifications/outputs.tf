output "main_topic_arn" {
  description = "ARN of the main support tickets SNS topic"
  value       = aws_sns_topic.support_tickets.arn
}

output "urgent_topic_arn" {
  description = "ARN of the urgent tickets SNS topic"
  value       = aws_sns_topic.urgent_tickets.arn
}

output "password_reset_topic_arn" {
  description = "ARN of the password reset tickets SNS topic"
  value       = aws_sns_topic.password_reset_tickets.arn
}

output "billing_topic_arn" {
  description = "ARN of the billing tickets SNS topic"
  value       = aws_sns_topic.billing_tickets.arn
}

output "technical_topic_arn" {
  description = "ARN of the technical tickets SNS topic"
  value       = aws_sns_topic.technical_tickets.arn
}

output "general_topic_arn" {
  description = "ARN of the general tickets SNS topic"
  value       = aws_sns_topic.general_tickets.arn
}

output "lambda_function_arn" {
  description = "ARN of the ticket router Lambda function"
  value       = aws_lambda_function.ticket_router.arn
}