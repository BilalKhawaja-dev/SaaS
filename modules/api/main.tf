# Network Load Balancer for VPC Link (required for API Gateway VPC Link)
resource "aws_lb" "nlb" {
  name               = "${var.project_name}-nlb"
  internal           = true
  load_balancer_type = "network"
  subnets            = var.private_subnet_ids

  enable_deletion_protection = false

  tags = var.tags
}

# Target Groups for each service
resource "aws_lb_target_group" "frontend" {
  name     = "${var.project_name}-frontend-tg"
  port     = 5002
  protocol = "TCP"
  vpc_id   = var.vpc_id
  target_type = "instance"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    port                = "5002"
    protocol            = "TCP"
    timeout             = 10
    unhealthy_threshold = 2
  }

  tags = var.tags
}

resource "aws_lb_target_group" "subscription" {
  name     = "${var.project_name}-subscription-tg"
  port     = 5000
  protocol = "TCP"
  vpc_id   = var.vpc_id
  target_type = "instance"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    port                = "5000"
    protocol            = "TCP"
    timeout             = 10
    unhealthy_threshold = 2
  }

  tags = var.tags
}

resource "aws_lb_target_group" "support" {
  name     = "${var.project_name}-support-tg"
  port     = 5001
  protocol = "TCP"
  vpc_id   = var.vpc_id
  target_type = "instance"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    port                = "5001"
    protocol            = "TCP"
    timeout             = 10
    unhealthy_threshold = 2
  }

  tags = var.tags
}

# NLB Listeners
resource "aws_lb_listener" "frontend" {
  load_balancer_arn = aws_lb.nlb.arn
  port              = "5002"
  protocol          = "TCP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

resource "aws_lb_listener" "subscription" {
  load_balancer_arn = aws_lb.nlb.arn
  port              = "5000"
  protocol          = "TCP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.subscription.arn
  }
}

resource "aws_lb_listener" "support" {
  load_balancer_arn = aws_lb.nlb.arn
  port              = "5001"
  protocol          = "TCP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.support.arn
  }
}

# VPC Link for API Gateway to NLB
resource "aws_api_gateway_vpc_link" "main" {
  name        = "${var.project_name}-vpc-link"
  target_arns = [aws_lb.nlb.arn]

  tags = var.tags
}

# API Gateway
resource "aws_api_gateway_rest_api" "main" {
  name        = "${var.project_name}-api"
  description = "SaaS Platform API"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = var.tags
}

# Lambda Authorizer Function
resource "aws_lambda_function" "authorizer" {
  filename         = "${path.module}/authorizer.zip"
  function_name    = "${var.project_name}-authorizer"
  role            = var.lambda_execution_role_arn
  handler         = "authorizer.handler"
  runtime         = "python3.11"
  timeout         = 30

  environment {
    variables = {
      USER_POOL_ID = var.user_pool_id
      CLIENT_ID    = var.user_pool_client_id
      REGION       = "eu-west-2"
    }
  }

  tags = var.tags
}

# API Gateway REQUEST Authorizer
resource "aws_api_gateway_authorizer" "lambda" {
  name                   = "${var.project_name}-lambda-authorizer"
  rest_api_id           = aws_api_gateway_rest_api.main.id
  type                  = "REQUEST"
  authorizer_uri        = aws_lambda_function.authorizer.invoke_arn
  identity_source       = "method.request.header.Authorization"
  authorizer_credentials = var.lambda_execution_role_arn
}

# Lambda permission for API Gateway
resource "aws_lambda_permission" "authorizer" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.authorizer.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# Root resource for frontend
resource "aws_api_gateway_method" "root_get" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_rest_api.main.root_resource_id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "root_get" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_rest_api.main.root_resource_id
  http_method             = aws_api_gateway_method.root_get.http_method
  type                    = "HTTP_PROXY"
  integration_http_method = "GET"
  uri                     = "http://${aws_lb.nlb.dns_name}:5002/"
  connection_type         = "VPC_LINK"
  connection_id           = aws_api_gateway_vpc_link.main.id
}

# API Gateway Resource - /api
resource "aws_api_gateway_resource" "api" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "api"
}

# API Gateway Resource - /api/subscription
resource "aws_api_gateway_resource" "subscription" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.api.id
  path_part   = "subscription"
}

# API Gateway Resource - /api/support
resource "aws_api_gateway_resource" "support" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.api.id
  path_part   = "support"
}

# Subscription service proxy
resource "aws_api_gateway_resource" "subscription_proxy" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.subscription.id
  path_part   = "{proxy+}"
}

resource "aws_api_gateway_method" "subscription_any" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.subscription_proxy.id
  http_method   = "ANY"
  authorization = "CUSTOM"
  authorizer_id = aws_api_gateway_authorizer.lambda.id

  request_parameters = {
    "method.request.path.proxy" = true
    "method.request.header.Authorization" = true
  }
}

resource "aws_api_gateway_integration" "subscription_any" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.subscription_proxy.id
  http_method             = aws_api_gateway_method.subscription_any.http_method
  type                    = "HTTP_PROXY"
  integration_http_method = "ANY"
  uri                     = "http://${aws_lb.nlb.dns_name}:5000/{proxy}"
  connection_type         = "VPC_LINK"
  connection_id           = aws_api_gateway_vpc_link.main.id

  request_parameters = {
    "integration.request.path.proxy" = "method.request.path.proxy"
  }
}

# Support service proxy
resource "aws_api_gateway_resource" "support_proxy" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.support.id
  path_part   = "{proxy+}"
}

resource "aws_api_gateway_method" "support_any" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.support_proxy.id
  http_method   = "ANY"
  authorization = "CUSTOM"
  authorizer_id = aws_api_gateway_authorizer.lambda.id

  request_parameters = {
    "method.request.path.proxy" = true
    "method.request.header.Authorization" = true
  }
}

resource "aws_api_gateway_integration" "support_any" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.support_proxy.id
  http_method             = aws_api_gateway_method.support_any.http_method
  type                    = "HTTP_PROXY"
  integration_http_method = "ANY"
  uri                     = "http://${aws_lb.nlb.dns_name}:5001/{proxy}"
  connection_type         = "VPC_LINK"
  connection_id           = aws_api_gateway_vpc_link.main.id

  request_parameters = {
    "integration.request.path.proxy" = "method.request.path.proxy"
  }
}

# API Gateway Deployment
resource "aws_api_gateway_deployment" "main" {
  depends_on = [
    aws_api_gateway_integration.root_get,
    aws_api_gateway_integration.subscription_any,
    aws_api_gateway_integration.support_any
  ]

  rest_api_id = aws_api_gateway_rest_api.main.id

  lifecycle {
    create_before_destroy = true
  }
}

# API Gateway Stage
resource "aws_api_gateway_stage" "dev" {
  deployment_id = aws_api_gateway_deployment.main.id
  rest_api_id   = aws_api_gateway_rest_api.main.id
  stage_name    = "dev"
}