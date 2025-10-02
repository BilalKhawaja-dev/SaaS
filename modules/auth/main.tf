# Cognito User Pool
resource "aws_cognito_user_pool" "main" {
  name = "${var.project_name}-user-pool"

  password_policy {
    minimum_length    = 12
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }

  auto_verified_attributes = ["email"]
  username_attributes      = ["email"]

  # Email configuration
  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }

  # Standard attributes
  schema {
    attribute_data_type = "String"
    name               = "email"
    required           = true
    mutable            = true
  }

  # Custom attributes for tenant information
  schema {
    attribute_data_type = "String"
    name               = "tenant_id"
    required           = false
    mutable            = true
    
    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  schema {
    attribute_data_type = "String"
    name               = "company_name"
    required           = false
    mutable            = true
    
    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  # Account recovery
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # Lambda triggers
  lambda_config {
    pre_token_generation = aws_lambda_function.token_customizer.arn
  }

  tags = var.tags
}

# Cognito User Pool Domain
resource "aws_cognito_user_pool_domain" "main" {
  domain       = "${var.project_name}-${random_string.domain_suffix.result}"
  user_pool_id = aws_cognito_user_pool.main.id
}

resource "random_string" "domain_suffix" {
  length  = 8
  special = false
  upper   = false
}

# Cognito User Pool Client
resource "aws_cognito_user_pool_client" "main" {
  name         = "${var.project_name}-client"
  user_pool_id = aws_cognito_user_pool.main.id

  generate_secret = false
  
  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_PASSWORD_AUTH"
  ]

  supported_identity_providers = ["COGNITO"]
  
  callback_urls = [
    "https://${var.api_gateway_domain}/callback",
    "http://localhost:3000/callback"  # For local development
  ]
  
  logout_urls = [
    "https://${var.api_gateway_domain}/logout",
    "http://localhost:3000/logout"   # For local development
  ]
  
  allowed_oauth_flows = ["code", "implicit"]
  allowed_oauth_scopes = ["email", "openid", "profile"]
  allowed_oauth_flows_user_pool_client = true
  
  # Token validity
  access_token_validity  = 60    # 1 hour
  id_token_validity     = 60    # 1 hour
  refresh_token_validity = 30   # 30 days
  
  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }

  # Prevent user existence errors
  prevent_user_existence_errors = "ENABLED"
}

# User Groups
resource "aws_cognito_user_group" "admin" {
  name         = "admin"
  user_pool_id = aws_cognito_user_pool.main.id
  description  = "Administrator group with full access"
  precedence   = 1
}

resource "aws_cognito_user_group" "user" {
  name         = "user"
  user_pool_id = aws_cognito_user_pool.main.id
  description  = "Regular user group with read-only access"
  precedence   = 2
}

resource "aws_cognito_user_group" "readonly" {
  name         = "readonly"
  user_pool_id = aws_cognito_user_pool.main.id
  description  = "Read-only access group"
  precedence   = 3
}

# Generate secure random passwords
resource "random_password" "admin_password" {
  length  = 16
  special = true
  upper   = true
  lower   = true
  numeric = true
}

resource "random_password" "user_password" {
  length  = 16
  special = true
  upper   = true
  lower   = true
  numeric = true
}

resource "random_password" "readonly_password" {
  length  = 16
  special = true
  upper   = true
  lower   = true
  numeric = true
}

# Demo Users matching database demo data
resource "aws_cognito_user" "admin_user" {
  user_pool_id = aws_cognito_user_pool.main.id
  username     = "admin@democorp.com"
  password     = "Admin123!"  # Fixed password for demo
  
  attributes = {
    email                    = "admin@democorp.com"
    email_verified          = "true"
    "custom:tenant_id"      = "550e8400-e29b-41d4-a716-446655440001"
    "custom:company_name"   = "Demo Corp"
  }
  
  message_action = "SUPPRESS"
}

resource "aws_cognito_user" "regular_user" {
  user_pool_id = aws_cognito_user_pool.main.id
  username     = "user@testinc.com"
  password     = "User123!"   # Fixed password for demo
  
  attributes = {
    email                    = "user@testinc.com"
    email_verified          = "true"
    "custom:tenant_id"      = "550e8400-e29b-41d4-a716-446655440002"
    "custom:company_name"   = "Test Inc"
  }
  
  message_action = "SUPPRESS"
}

resource "aws_cognito_user" "readonly_user" {
  user_pool_id = aws_cognito_user_pool.main.id
  username     = "readonly@enterpriseltd.com"
  password     = "Readonly123!"  # Fixed password for demo
  
  attributes = {
    email                    = "readonly@enterpriseltd.com"
    email_verified          = "true"
    "custom:tenant_id"      = "550e8400-e29b-41d4-a716-446655440003"
    "custom:company_name"   = "Enterprise Ltd"
  }
  
  message_action = "SUPPRESS"
}

# User Group Memberships
resource "aws_cognito_user_in_group" "admin_membership" {
  user_pool_id = aws_cognito_user_pool.main.id
  group_name   = aws_cognito_user_group.admin.name
  username     = aws_cognito_user.admin_user.username
}

resource "aws_cognito_user_in_group" "user_membership" {
  user_pool_id = aws_cognito_user_pool.main.id
  group_name   = aws_cognito_user_group.user.name
  username     = aws_cognito_user.regular_user.username
}

resource "aws_cognito_user_in_group" "readonly_membership" {
  user_pool_id = aws_cognito_user_pool.main.id
  group_name   = aws_cognito_user_group.readonly.name
  username     = aws_cognito_user.readonly_user.username
}

# Lambda function for token customization
resource "aws_lambda_function" "token_customizer" {
  filename         = "${path.module}/token_customizer.zip"
  function_name    = "${var.project_name}-token-customizer"
  role            = aws_iam_role.token_customizer_role.arn
  handler         = "token_customizer.handler"
  runtime         = "python3.11"
  timeout         = 30

  tags = var.tags
}

# IAM role for token customizer Lambda
resource "aws_iam_role" "token_customizer_role" {
  name = "${var.project_name}-token-customizer-role"

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

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "token_customizer_basic" {
  role       = aws_iam_role.token_customizer_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Lambda permission for Cognito
resource "aws_lambda_permission" "cognito_token_customizer" {
  statement_id  = "AllowExecutionFromCognito"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.token_customizer.function_name
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.main.arn
}

# Store Cognito configuration in SSM Parameter Store
resource "aws_ssm_parameter" "user_pool_id" {
  name  = "/${var.project_name}/cognito/user_pool_id"
  type  = "String"
  value = aws_cognito_user_pool.main.id
  tags  = var.tags
}

resource "aws_ssm_parameter" "user_pool_client_id" {
  name  = "/${var.project_name}/cognito/client_id"
  type  = "String"
  value = aws_cognito_user_pool_client.main.id
  tags  = var.tags
}