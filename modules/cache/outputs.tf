output "valkey_endpoint" {
  description = "Valkey cluster endpoint"
  value       = aws_elasticache_cluster.main.cache_nodes[0].address
}

output "valkey_port" {
  description = "Valkey cluster port"
  value       = aws_elasticache_cluster.main.cache_nodes[0].port
}