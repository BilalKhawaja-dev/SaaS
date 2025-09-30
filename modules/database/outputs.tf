output "rds_endpoint" {
  description = "RDS Proxy endpoint"
  value       = aws_db_proxy.main.endpoint
}

output "rds_port" {
  description = "RDS port"
  value       = 5432
}

output "aurora_cluster_endpoint" {
  description = "Aurora cluster endpoint"
  value       = aws_rds_cluster.main.endpoint
}

output "aurora_reader_endpoint" {
  description = "Aurora reader endpoint"
  value       = aws_rds_cluster.main.reader_endpoint
}

output "support_tickets_table_name" {
  description = "DynamoDB support tickets table name"
  value       = aws_dynamodb_table.support_tickets.name
}

output "user_sessions_table_name" {
  description = "DynamoDB user sessions table name"
  value       = aws_dynamodb_table.user_sessions.name
}

output "rds_instance_id" {
  description = "Aurora cluster identifier"
  value       = aws_rds_cluster.main.cluster_identifier
}

output "dax_cluster_endpoint" {
  description = "DAX cluster endpoint"
  value       = aws_dax_cluster.main.cluster_address
}