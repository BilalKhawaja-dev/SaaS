# ElastiCache Subnet Group
resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.project_name}-cache-subnet-group"
  subnet_ids = [var.private_subnet_id]

  tags = var.tags
}

# ElastiCache Valkey Cluster
resource "aws_elasticache_cluster" "main" {
  cluster_id           = "${var.project_name}-cache"
  engine               = "valkey"
  engine_version       = "8.0"
  node_type            = var.elasticache_node_type
  num_cache_nodes      = 1
  parameter_group_name = "default.valkey8"
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [var.elasticache_security_group_id]

  tags = merge(var.tags, {
    Name = "${var.project_name}-cache"
  })
}