# VPC Link for API Gateway to ECS
resource "aws_api_gateway_vpc_link" "main" {
  name        = "${var.project_name}-vpc-link"
  target_arns = [var.alb_arn]

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
  uri                     = "http://${var.alb_dns_name}/"
  connection_type         = "VPC_LINK"
  connection_id           = aws_api_gateway_vpc_link.main.id
}

# API Gateway Resource - /api
resource "aws_api_gateway_resource" "api" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "api"
}

# API Gateway Resource - /api/auth
resource "aws_api_gateway_resource" "auth" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.api.id
  path_part   = "auth"
}

# API Gateway Resource - /api/balance
resource "aws_api_gateway_resource" "balance" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.api.id
  path_part   = "balance"
}

# API Gateway Resource - /api/support
resource "aws_api_gateway_resource" "support" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.api.id
  path_part   = "support"
}

# Proxy resource for all API calls
resource "aws_api_gateway_resource" "api_proxy" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.api.id
  path_part   = "{proxy+}"
}

resource "aws_api_gateway_method" "api_any" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.api_proxy.id
  http_method   = "ANY"
  authorization = "NONE"  # Let services handle their own auth

  request_parameters = {
    "method.request.path.proxy" = true
  }
}

resource "aws_api_gateway_integration" "api_any" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.api_proxy.id
  http_method             = aws_api_gateway_method.api_any.http_method
  type                    = "HTTP_PROXY"
  integration_http_method = "ANY"
  uri                     = "http://${var.alb_dns_name}/api/{proxy}"
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
    aws_api_gateway_integration.api_any
  ]

  rest_api_id = aws_api_gateway_rest_api.main.id
  stage_name  = "dev"

  lifecycle {
    create_before_destroy = true
  }
}