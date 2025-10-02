# ElastiCache Subnet Group
resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.project_name}-cache-subnet-group"
  subnet_ids = var.private_subnet_ids

  tags = var.tags
}

# ElastiCache Valkey Replication Group (Multi-AZ)
resource "aws_elasticache_replication_group" "main" {
  replication_group_id       = "${var.project_name}-cache"
  description                = "Valkey cluster for ${var.project_name}"
  
  engine               = "valkey"
  engine_version       = "8.0"
  node_type            = var.elasticache_node_type
  port                 = 6379
  parameter_group_name = "default.valkey8"
  
  num_cache_clusters = 2  # Multi-AZ with 2 nodes
  
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [var.elasticache_security_group_id]
  
  # Multi-AZ configuration
  multi_az_enabled           = true
  automatic_failover_enabled = true
  
  # Backup configuration
  snapshot_retention_limit = 3
  snapshot_window         = "03:00-05:00"
  maintenance_window      = "sun:05:00-sun:07:00"

  tags = merge(var.tags, {
    Name = "${var.project_name}-cache"
  })
}

# Store cache endpoints in SSM Parameter Store
resource "aws_ssm_parameter" "valkey_endpoint" {
  name  = "/${var.project_name}/cache/valkey/endpoint"
  type  = "String"
  value = aws_elasticache_replication_group.main.primary_endpoint_address
  tags  = var.tags
}

resource "aws_ssm_parameter" "valkey_port" {
  name  = "/${var.project_name}/cache/valkey/port"
  type  = "String"
  value = tostring(aws_elasticache_replication_group.main.port)
  tags  = var.tags
}

resource "aws_ssm_parameter" "valkey_reader_endpoint" {
  name  = "/${var.project_name}/cache/valkey/reader_endpoint"
  type  = "String"
  value = aws_elasticache_replication_group.main.reader_endpoint_address
  tags  = var.tags
}