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

# Enterprise CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "enterprise" {
  dashboard_name = "${var.project_name}-enterprise-dashboard"

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
            ["AWS/ApiGateway", "Count", "ApiName", "${var.project_name}-api"],
            ["AWS/ApiGateway", "Latency", "ApiName", "${var.project_name}-api"],
            ["AWS/ApiGateway", "4XXError", "ApiName", "${var.project_name}-api"],
            ["AWS/ApiGateway", "5XXError", "ApiName", "${var.project_name}-api"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "eu-west-2"
          title   = "API Gateway Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/ECS", "CPUUtilization", "ServiceName", "${var.project_name}-frontend", "ClusterName", "${var.project_name}-cluster"],
            ["AWS/ECS", "MemoryUtilization", "ServiceName", "${var.project_name}-frontend", "ClusterName", "${var.project_name}-cluster"],
            ["AWS/ECS", "CPUUtilization", "ServiceName", "${var.project_name}-subscription-service", "ClusterName", "${var.project_name}-cluster"],
            ["AWS/ECS", "CPUUtilization", "ServiceName", "${var.project_name}-support-service", "ClusterName", "${var.project_name}-cluster"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "eu-west-2"
          title   = "ECS Services CPU/Memory"
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
            ["AWS/RDS", "DatabaseConnections", "DBClusterIdentifier", "${var.project_name}-aurora-cluster"],
            ["AWS/RDS", "ReadLatency", "DBClusterIdentifier", "${var.project_name}-aurora-cluster"],
            ["AWS/RDS", "WriteLatency", "DBClusterIdentifier", "${var.project_name}-aurora-cluster"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "eu-west-2"
          title   = "Aurora Database Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/ECS", "RunningTaskCount", "ServiceName", "${var.project_name}-frontend", "ClusterName", "${var.project_name}-cluster"],
            ["AWS/ECS", "RunningTaskCount", "ServiceName", "${var.project_name}-subscription-service", "ClusterName", "${var.project_name}-cluster"],
            ["AWS/ECS", "RunningTaskCount", "ServiceName", "${var.project_name}-support-service", "ClusterName", "${var.project_name}-cluster"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "eu-west-2"
          title   = "ECS Running Tasks"
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
            ["AWS/EC2", "CPUUtilization", "AutoScalingGroupName", "${var.project_name}-ecs-asg"],
            ["AWS/AutoScaling", "GroupDesiredCapacity", "AutoScalingGroupName", "${var.project_name}-ecs-asg"],
            ["AWS/AutoScaling", "GroupInServiceInstances", "AutoScalingGroupName", "${var.project_name}-ecs-asg"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "eu-west-2"
          title   = "Auto Scaling Infrastructure"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 12
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", "${var.project_name}-authorizer"],
            ["AWS/Lambda", "Invocations", "FunctionName", "${var.project_name}-authorizer"],
            ["AWS/Lambda", "Errors", "FunctionName", "${var.project_name}-authorizer"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "eu-west-2"
          title   = "Lambda Authorizer Metrics"
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
            ["AWS/ElastiCache", "CPUUtilization", "CacheClusterId", "${var.project_name}-cache-001"],
            ["AWS/ElastiCache", "NetworkBytesIn", "CacheClusterId", "${var.project_name}-cache-001"],
            ["AWS/ElastiCache", "NetworkBytesOut", "CacheClusterId", "${var.project_name}-cache-001"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "eu-west-2"
          title   = "Valkey Cache Performance"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 18
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/DAX", "CPUUtilization", "ClusterName", "${var.project_name}-dax-cluster"],
            ["AWS/DAX", "ItemCacheHits", "ClusterName", "${var.project_name}-dax-cluster"],
            ["AWS/DAX", "ItemCacheMisses", "ClusterName", "${var.project_name}-dax-cluster"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "eu-west-2"
          title   = "DAX Performance Metrics"
          period  = 300
        }
      }
    ]
  })
}

# CloudWatch Alarms for API Gateway
resource "aws_cloudwatch_metric_alarm" "api_gateway_4xx_errors" {
  alarm_name          = "${var.project_name}-api-gateway-4xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "4XXError"
  namespace           = "AWS/ApiGateway"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "This metric monitors API Gateway 4XX errors"

  dimensions = {
    ApiName = "${var.project_name}-api"
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "api_gateway_5xx_errors" {
  alarm_name          = "${var.project_name}-api-gateway-5xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "5XXError"
  namespace           = "AWS/ApiGateway"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors API Gateway 5XX errors"

  dimensions = {
    ApiName = "${var.project_name}-api"
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "api_gateway_latency" {
  alarm_name          = "${var.project_name}-api-gateway-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Latency"
  namespace           = "AWS/ApiGateway"
  period              = "300"
  statistic           = "Average"
  threshold           = "5000" # 5 seconds
  alarm_description   = "This metric monitors API Gateway latency"

  dimensions = {
    ApiName = "${var.project_name}-api"
  }

  tags = var.tags
}

# CloudWatch Alarms for Lambda Authorizer
resource "aws_cloudwatch_metric_alarm" "lambda_authorizer_errors" {
  alarm_name          = "${var.project_name}-lambda-authorizer-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors Lambda authorizer errors"

  dimensions = {
    FunctionName = "${var.project_name}-authorizer"
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "lambda_authorizer_duration" {
  alarm_name          = "${var.project_name}-lambda-authorizer-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Average"
  threshold           = "10000" # 10 seconds
  alarm_description   = "This metric monitors Lambda authorizer duration"

  dimensions = {
    FunctionName = "${var.project_name}-authorizer"
  }

  tags = var.tags
}

# CloudWatch Alarms for Cache Performance
resource "aws_cloudwatch_metric_alarm" "valkey_cpu_high" {
  alarm_name          = "${var.project_name}-valkey-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors Valkey CPU utilization"

  dimensions = {
    CacheClusterId = "${var.project_name}-cache-001"
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "dax_cpu_high" {
  alarm_name          = "${var.project_name}-dax-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/DAX"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors DAX CPU utilization"

  dimensions = {
    ClusterName = "${var.project_name}-dax-cluster"
  }

  tags = var.tags
}