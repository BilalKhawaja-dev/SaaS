# CloudWatch Log Group for Application Logs
resource "aws_cloudwatch_log_group" "app_logs" {
  name              = "/aws/ecs/${var.project_name}"
  retention_in_days = 7

  tags = var.tags
}

# CloudWatch Log Group for API Gateway
resource "aws_cloudwatch_log_group" "api_logs" {
  name              = "/aws/apigateway/${var.project_name}"
  retention_in_days = 7

  tags = var.tags
}

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.project_name}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/ECS", "CPUUtilization", "ServiceName", "${var.project_name}-frontend", "ClusterName", "${var.project_name}-cluster"],
            ["AWS/ECS", "MemoryUtilization", "ServiceName", "${var.project_name}-frontend", "ClusterName", "${var.project_name}-cluster"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "eu-west-2"
          title   = "ECS Service Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/RDS", "CPUUtilization", "DBClusterIdentifier", "${var.project_name}-aurora-cluster"],
            ["AWS/RDS", "DatabaseConnections", "DBClusterIdentifier", "${var.project_name}-aurora-cluster"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "eu-west-2"
          title   = "Aurora Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", "${var.project_name}-alb"],
            ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", "${var.project_name}-alb"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "eu-west-2"
          title   = "Load Balancer Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 18
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/EC2", "CPUUtilization", "AutoScalingGroupName", "${var.project_name}-ecs-asg"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "eu-west-2"
          title   = "Auto Scaling Group CPU"
          period  = 300
        }
      }
    ]
  })
}