# SNS Topics and Lambda-based intelligent routing for support tickets

# Main SNS topic for all support tickets
resource "aws_sns_topic" "support_tickets" {
  name = "${var.project_name}-support-tickets"
  
  tags = {
    Name        = "${var.project_name}-support-tickets"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Urgent tickets topic (routes to your email)
resource "aws_sns_topic" "urgent_tickets" {
  name = "${var.project_name}-urgent-tickets"
  
  tags = {
    Name        = "${var.project_name}-urgent-tickets"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Password reset tickets topic
resource "aws_sns_topic" "password_reset_tickets" {
  name = "${var.project_name}-password-reset-tickets"
  
  tags = {
    Name        = "${var.project_name}-password-reset-tickets"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Billing tickets topic
resource "aws_sns_topic" "billing_tickets" {
  name = "${var.project_name}-billing-tickets"
  
  tags = {
    Name        = "${var.project_name}-billing-tickets"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Technical support tickets topic
resource "aws_sns_topic" "technical_tickets" {
  name = "${var.project_name}-technical-tickets"
  
  tags = {
    Name        = "${var.project_name}-technical-tickets"
    Environment = var.environment
    Project     = var.project_name
  }
}

# General support tickets topic
resource "aws_sns_topic" "general_tickets" {
  name = "${var.project_name}-general-tickets"
  
  tags = {
    Name        = "${var.project_name}-general-tickets"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Email subscriptions
resource "aws_sns_topic_subscription" "urgent_email" {
  topic_arn = aws_sns_topic.urgent_tickets.arn
  protocol  = "email"
  endpoint  = "bilalkwj@amazon.com"
}

resource "aws_sns_topic_subscription" "password_reset_email" {
  topic_arn = aws_sns_topic.password_reset_tickets.arn
  protocol  = "email"
  endpoint  = "support-password@example.com"
}

resource "aws_sns_topic_subscription" "billing_email" {
  topic_arn = aws_sns_topic.billing_tickets.arn
  protocol  = "email"
  endpoint  = "billing-support@example.com"
}

resource "aws_sns_topic_subscription" "technical_email" {
  topic_arn = aws_sns_topic.technical_tickets.arn
  protocol  = "email"
  endpoint  = "tech-support@example.com"
}

resource "aws_sns_topic_subscription" "general_email" {
  topic_arn = aws_sns_topic.general_tickets.arn
  protocol  = "email"
  endpoint  = "general-support@example.com"
}

# IAM role for Lambda function
resource "aws_iam_role" "ticket_router_lambda_role" {
  name = "${var.project_name}-ticket-router-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# IAM policy for Lambda function
resource "aws_iam_role_policy" "ticket_router_lambda_policy" {
  name = "${var.project_name}-ticket-router-lambda-policy"
  role = aws_iam_role.ticket_router_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = [
          aws_sns_topic.urgent_tickets.arn,
          aws_sns_topic.password_reset_tickets.arn,
          aws_sns_topic.billing_tickets.arn,
          aws_sns_topic.technical_tickets.arn,
          aws_sns_topic.general_tickets.arn
        ]
      }
    ]
  })
}

# Lambda function for intelligent ticket routing
resource "aws_lambda_function" "ticket_router" {
  filename         = "${path.module}/ticket_router.zip"
  function_name    = "${var.project_name}-ticket-router"
  role            = aws_iam_role.ticket_router_lambda_role.arn
  handler         = "ticket_router.lambda_handler"
  runtime         = "python3.11"
  timeout         = 30

  environment {
    variables = {
      URGENT_TOPIC_ARN = aws_sns_topic.urgent_tickets.arn
      PASSWORD_RESET_TOPIC_ARN = aws_sns_topic.password_reset_tickets.arn
      BILLING_TOPIC_ARN = aws_sns_topic.billing_tickets.arn
      TECHNICAL_TOPIC_ARN = aws_sns_topic.technical_tickets.arn
      GENERAL_TOPIC_ARN = aws_sns_topic.general_tickets.arn
    }
  }

  depends_on = [
    aws_iam_role_policy.ticket_router_lambda_policy,
    aws_cloudwatch_log_group.ticket_router_logs,
    data.archive_file.ticket_router_zip
  ]

  tags = {
    Name        = "${var.project_name}-ticket-router"
    Environment = var.environment
    Project     = var.project_name
  }
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "ticket_router_logs" {
  name              = "/aws/lambda/${var.project_name}-ticket-router"
  retention_in_days = 14

  tags = {
    Name        = "${var.project_name}-ticket-router-logs"
    Environment = var.environment
    Project     = var.project_name
  }
}

# SNS topic subscription for Lambda
resource "aws_sns_topic_subscription" "ticket_router_lambda" {
  topic_arn = aws_sns_topic.support_tickets.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.ticket_router.arn
}

# Lambda permission for SNS
resource "aws_lambda_permission" "allow_sns" {
  statement_id  = "AllowExecutionFromSNS"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ticket_router.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.support_tickets.arn
}

# Create Lambda deployment package
data "archive_file" "ticket_router_zip" {
  type        = "zip"
  output_path = "${path.module}/ticket_router.zip"
  source {
    content  = file("${path.module}/ticket_router.py")
    filename = "ticket_router.py"
  }
}

# Store SNS topic ARN in SSM for services to use
resource "aws_ssm_parameter" "sns_topic_arn" {
  name  = "/saas-platform/notifications/sns_topic_arn"
  type  = "String"
  value = aws_sns_topic.support_tickets.arn

  tags = {
    Name        = "${var.project_name}-sns-topic-arn"
    Environment = var.environment
    Project     = var.project_name
  }
}