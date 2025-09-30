# Cognito User Pool
resource "aws_cognito_user_pool" "main" {
  name = "${var.project_name}-user-pool"

  password_policy {
    minimum_length    = 6
    require_lowercase = false
    require_numbers   = false
    require_symbols   = false
    require_uppercase = false
  }

  auto_verified_attributes = ["email"]
  username_attributes      = ["email"]

  schema {
    attribute_data_type = "String"
    name               = "email"
    required           = true
    mutable            = true
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
    "ALLOW_REFRESH_TOKEN_AUTH"
  ]

  supported_identity_providers = ["COGNITO"]
  
  callback_urls = [
    "https://${var.api_gateway_domain}/callback"
  ]
  
  logout_urls = [
    "https://${var.api_gateway_domain}/logout"
  ]
  
  allowed_oauth_flows = ["code"]
  allowed_oauth_scopes = ["email", "openid", "profile"]
  allowed_oauth_flows_user_pool_client = true
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

# Demo Users
resource "aws_cognito_user" "admin_user" {
  user_pool_id = aws_cognito_user_pool.main.id
  username     = "admin@demo.com"
  password     = "admin123"
  
  attributes = {
    email          = "admin@demo.com"
    email_verified = true
  }
  
  message_action = "SUPPRESS"
}

resource "aws_cognito_user" "regular_user" {
  user_pool_id = aws_cognito_user_pool.main.id
  username     = "user@demo.com"
  password     = "user123"
  
  attributes = {
    email          = "user@demo.com"
    email_verified = true
  }
  
  message_action = "SUPPRESS"
}

resource "aws_cognito_user" "readonly_user" {
  user_pool_id = aws_cognito_user_pool.main.id
  username     = "readonly@demo.com"
  password     = "readonly123"
  
  attributes = {
    email          = "readonly@demo.com"
    email_verified = true
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