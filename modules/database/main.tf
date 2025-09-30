# Generate random password
resource "random_password" "db_password" {
  length  = 16
  special = true
}

# Store password in Secrets Manager
resource "aws_secretsmanager_secret" "db_password" {
  name = "${var.project_name}/database/password"
  tags = var.tags
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = jsonencode({
    username = var.db_username
    password = random_password.db_password.result
  })
}

# Store DB endpoint in SSM Parameter Store
resource "aws_ssm_parameter" "db_endpoint" {
  name  = "/${var.project_name}/database/endpoint"
  type  = "String"
  value = aws_db_instance.main.endpoint
  tags  = var.tags
}

resource "aws_ssm_parameter" "db_name" {
  name  = "/${var.project_name}/database/name"
  type  = "String"
  value = "saasdb"
  tags  = var.tags
}

# DB Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet-group"
  subnet_ids = [var.private_subnet_id] # Single AZ for cost optimization

  tags = merge(var.tags, {
    Name = "${var.project_name}-db-subnet-group"
  })
}

# RDS Instance
resource "aws_db_instance" "main" {
  identifier     = "${var.project_name}-db"
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = var.rds_instance_class
  
  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type         = "gp2"
  storage_encrypted    = true
  
  db_name  = "saasdb"
  username = var.db_username
  password = random_password.db_password.result
  
  vpc_security_group_ids = [var.rds_security_group_id]
  db_subnet_group_name   = aws_db_subnet_group.main.name
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  skip_final_snapshot = true
  deletion_protection = false
  
  tags = merge(var.tags, {
    Name = "${var.project_name}-db"
  })
}

# DynamoDB Table for Support Tickets
resource "aws_dynamodb_table" "support_tickets" {
  name           = "${var.project_name}-support-tickets"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "tenant_id"
  range_key      = "ticket_id"

  attribute {
    name = "tenant_id"
    type = "S"
  }

  attribute {
    name = "ticket_id"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  global_secondary_index {
    name     = "status-index"
    hash_key = "status"
  }

  server_side_encryption {
    enabled = true
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-support-tickets"
  })
}

# DynamoDB Table for User Sessions
resource "aws_dynamodb_table" "user_sessions" {
  name           = "${var.project_name}-user-sessions"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "session_id"

  attribute {
    name = "session_id"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-user-sessions"
  })
}