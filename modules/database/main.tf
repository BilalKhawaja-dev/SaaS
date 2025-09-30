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
  value = aws_db_proxy.main.endpoint
  tags  = var.tags
}

resource "aws_ssm_parameter" "db_cluster_endpoint" {
  name  = "/${var.project_name}/database/cluster_endpoint"
  type  = "String"
  value = aws_rds_cluster.main.endpoint
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

# Aurora Serverless v2 Cluster
resource "aws_rds_cluster" "main" {
  cluster_identifier     = "${var.project_name}-aurora-cluster"
  engine                = "aurora-postgresql"
  engine_mode           = "provisioned"
  engine_version        = "15.4"
  database_name         = "saasdb"
  master_username       = var.db_username
  master_password       = random_password.db_password.result
  
  vpc_security_group_ids = [var.rds_security_group_id]
  db_subnet_group_name   = aws_db_subnet_group.main.name
  
  backup_retention_period = 7
  preferred_backup_window = "03:00-04:00"
  preferred_maintenance_window = "sun:04:00-sun:05:00"
  
  storage_encrypted = true
  skip_final_snapshot = true
  deletion_protection = false
  
  serverlessv2_scaling_configuration {
    max_capacity = 1
    min_capacity = 0.5
  }
  
  tags = merge(var.tags, {
    Name = "${var.project_name}-aurora-cluster"
  })
}

# Aurora Serverless v2 Instance
resource "aws_rds_cluster_instance" "main" {
  identifier         = "${var.project_name}-aurora-instance"
  cluster_identifier = aws_rds_cluster.main.id
  instance_class     = "db.serverless"
  engine            = aws_rds_cluster.main.engine
  engine_version    = aws_rds_cluster.main.engine_version
  
  tags = merge(var.tags, {
    Name = "${var.project_name}-aurora-instance"
  })
}

# RDS Proxy
resource "aws_db_proxy" "main" {
  name                   = "${var.project_name}-rds-proxy"
  engine_family         = "POSTGRESQL"
  auth {
    auth_scheme = "SECRETS"
    secret_arn  = aws_secretsmanager_secret.db_password.arn
  }
  role_arn               = aws_iam_role.rds_proxy.arn
  vpc_subnet_ids         = [var.private_subnet_id]
  vpc_security_group_ids = [var.rds_security_group_id]
  
  target {
    db_cluster_identifier = aws_rds_cluster.main.cluster_identifier
  }
  
  tags = var.tags
}

# RDS Proxy IAM Role
resource "aws_iam_role" "rds_proxy" {
  name = "${var.project_name}-rds-proxy-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "rds.amazonaws.com"
        }
      }
    ]
  })
  
  tags = var.tags
}

resource "aws_iam_role_policy" "rds_proxy" {
  name = "${var.project_name}-rds-proxy-policy"
  role = aws_iam_role.rds_proxy.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = aws_secretsmanager_secret.db_password.arn
      }
    ]
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

# DAX Subnet Group
resource "aws_dax_subnet_group" "main" {
  name       = "${var.project_name}-dax-subnet-group"
  subnet_ids = [var.private_subnet_id]

  tags = var.tags
}

# DAX Cluster
resource "aws_dax_cluster" "main" {
  cluster_name       = "${var.project_name}-dax-cluster"
  iam_role_arn      = aws_iam_role.dax.arn
  node_type         = "dax.t3.small"
  replication_factor = 1
  
  subnet_group_name   = aws_dax_subnet_group.main.name
  security_group_ids  = [aws_security_group.dax.id]
  
  tags = var.tags
}

# DAX Security Group
resource "aws_security_group" "dax" {
  name_prefix = "${var.project_name}-dax-"
  vpc_id      = var.vpc_id
  
  ingress {
    from_port   = 8111
    to_port     = 8111
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = merge(var.tags, {
    Name = "${var.project_name}-dax-sg"
  })
}

# DAX IAM Role
resource "aws_iam_role" "dax" {
  name = "${var.project_name}-dax-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "dax.amazonaws.com"
        }
      }
    ]
  })
  
  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "dax" {
  role       = aws_iam_role.dax.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonDaxFullAccess"
}