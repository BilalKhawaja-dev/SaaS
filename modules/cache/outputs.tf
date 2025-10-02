output "valkey_endpoint" {
  description = "Valkey primary endpoint"
  value       = aws_elasticache_replication_group.main.primary_endpoint_address
}

output "valkey_port" {
  description = "Valkey cluster port"
  value       = aws_elasticache_replication_group.main.port
}

output "valkey_reader_endpoint" {
  description = "Valkey reader endpoint"
  value       = aws_elasticache_replication_group.main.reader_endpoint_address
}