# Data sources for dynamic values
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = var.tags
}

# Launch Template for ECS Instances
resource "aws_launch_template" "ecs" {
  name_prefix   = "${var.project_name}-ecs-"
  image_id      = data.aws_ami.ecs_optimized.id
  instance_type = var.ecs_instance_type

  vpc_security_group_ids = [var.ecs_security_group_id]

  iam_instance_profile {
    name = var.ecs_instance_profile_name
  }

  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    cluster_name = aws_ecs_cluster.main.name
  }))

  tag_specifications {
    resource_type = "instance"
    tags = merge(var.tags, {
      Name = "${var.project_name}-ecs-instance"
    })
  }
}

# Auto Scaling Group
resource "aws_autoscaling_group" "ecs" {
  name                = "${var.project_name}-ecs-asg"
  vpc_zone_identifier = var.private_subnet_ids
  min_size            = 1
  max_size            = 3
  desired_capacity    = 1
  
  target_group_arns = [
    var.nlb_target_group_frontend_arn,
    var.nlb_target_group_subscription_arn,
    var.nlb_target_group_support_arn
  ]
  
  health_check_type         = "ELB"
  health_check_grace_period = 900

  launch_template {
    id      = aws_launch_template.ecs.id
    version = "$Latest"
  }

  tag {
    key                 = "Name"
    value               = "${var.project_name}-ecs-asg"
    propagate_at_launch = false
  }

  dynamic "tag" {
    for_each = var.tags
    content {
      key                 = tag.key
      value               = tag.value
      propagate_at_launch = true
    }
  }
}

# Auto Scaling Policy - Scale Up
resource "aws_autoscaling_policy" "scale_up" {
  name                   = "${var.project_name}-scale-up"
  scaling_adjustment     = 1
  adjustment_type        = "ChangeInCapacity"
  cooldown              = 300
  autoscaling_group_name = aws_autoscaling_group.ecs.name
}

# Auto Scaling Policy - Scale Down
resource "aws_autoscaling_policy" "scale_down" {
  name                   = "${var.project_name}-scale-down"
  scaling_adjustment     = -1
  adjustment_type        = "ChangeInCapacity"
  cooldown              = 300
  autoscaling_group_name = aws_autoscaling_group.ecs.name
}

# CloudWatch Alarm - High CPU
resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "${var.project_name}-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "90"
  alarm_description   = "This metric monitors ECS cluster CPU utilization"
  alarm_actions       = [aws_autoscaling_policy.scale_up.arn, var.sns_topic_arn]

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
  }

  tags = var.tags
}

# CloudWatch Alarm - Low CPU
resource "aws_cloudwatch_metric_alarm" "cpu_low" {
  alarm_name          = "${var.project_name}-cpu-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "20"
  alarm_description   = "This metric monitors ECS cluster CPU utilization"
  alarm_actions       = [aws_autoscaling_policy.scale_down.arn]

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
  }

  tags = var.tags
}

# CloudWatch Alarm - Service Health
resource "aws_cloudwatch_metric_alarm" "service_count_low" {
  alarm_name          = "${var.project_name}-service-count-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "RunningTaskCount"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "1"
  alarm_description   = "This metric monitors ECS service running task count"
  alarm_actions       = [var.sns_topic_arn]

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.frontend.name
  }

  tags = var.tags
}



# Data source for ECS optimized AMI
data "aws_ami" "ecs_optimized" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-ecs-hvm-*-x86_64-ebs"]
  }
}

# ECS Task Definitions
resource "aws_ecs_task_definition" "frontend" {
  family                   = "${var.project_name}-frontend"
  network_mode             = "bridge"
  requires_compatibilities = ["EC2"]
  execution_role_arn       = var.ecs_execution_role_arn
  task_role_arn           = var.ecs_task_role_arn

  container_definitions = jsonencode([
    {
      name   = "frontend"
      image  = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com/${var.project_name}/frontend:latest"
      memory = 256
      portMappings = [
        {
          containerPort = 80
          hostPort      = 5002
          protocol      = "tcp"
        }
      ]
      essential = true
      healthCheck = {
        command = ["CMD-SHELL", "curl -f http://localhost:80/ || exit 1"]
        interval = 30
        timeout = 10
        retries = 3
        startPeriod = 30
      }
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = var.log_group_name
          "awslogs-region"        = "eu-west-2"
          "awslogs-stream-prefix" = "frontend"
        }
      }
    }
  ])

  tags = var.tags
}

resource "aws_ecs_task_definition" "subscription_service" {
  family                   = "${var.project_name}-subscription-service"
  network_mode             = "bridge"
  requires_compatibilities = ["EC2"]
  execution_role_arn       = var.ecs_execution_role_arn
  task_role_arn           = var.ecs_task_role_arn

  container_definitions = jsonencode([
    {
      name   = "subscription-service"
      image  = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com/${var.project_name}/subscription-service:latest"
      memory = 256
      portMappings = [
        {
          containerPort = 5000
          hostPort      = 5000
          protocol      = "tcp"
        }
      ]
      essential = true
      environment = [
        {
          name  = "AWS_DEFAULT_REGION"
          value = "eu-west-2"
        },
        {
          name  = "USER_POOL_ID"
          value = var.user_pool_id
        },
        {
          name  = "CLIENT_ID"
          value = var.user_pool_client_id
        }
      ]

      healthCheck = {
        command = ["CMD-SHELL", "curl -f http://localhost:5000/health || exit 1"]
        interval = 30
        timeout = 10
        retries = 3
        startPeriod = 60
      }
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = var.log_group_name
          "awslogs-region"        = "eu-west-2"
          "awslogs-stream-prefix" = "subscription-service"
        }
      }
    }
  ])

  tags = var.tags
}

resource "aws_ecs_task_definition" "support_service" {
  family                   = "${var.project_name}-support-service"
  network_mode             = "bridge"
  requires_compatibilities = ["EC2"]
  execution_role_arn       = var.ecs_execution_role_arn
  task_role_arn           = var.ecs_task_role_arn

  container_definitions = jsonencode([
    {
      name   = "support-service"
      image  = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com/${var.project_name}/support-service:latest"
      memory = 256
      portMappings = [
        {
          containerPort = 5001
          hostPort      = 5001
          protocol      = "tcp"
        }
      ]
      essential = true
      environment = [
        {
          name  = "AWS_DEFAULT_REGION"
          value = "eu-west-2"
        },
        {
          name  = "USER_POOL_ID"
          value = var.user_pool_id
        },
        {
          name  = "CLIENT_ID"
          value = var.user_pool_client_id
        },
        {
          name  = "SNS_TOPIC_ARN"
          value = var.sns_topic_arn
        },
        {
          name  = "DYNAMODB_TABLE_NAME"
          value = "${var.project_name}-tickets"
        }
      ]

      healthCheck = {
        command = ["CMD-SHELL", "curl -f http://localhost:5001/health || exit 1"]
        interval = 30
        timeout = 10
        retries = 3
        startPeriod = 60
      }
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = var.log_group_name
          "awslogs-region"        = "eu-west-2"
          "awslogs-stream-prefix" = "support-service"
        }
      }
    }
  ])

  tags = var.tags
}

# ECS Services
resource "aws_ecs_service" "frontend" {
  name            = "${var.project_name}-frontend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = 1

  placement_constraints {
    type = "distinctInstance"
  }

  tags = var.tags
}

resource "aws_ecs_service" "subscription_service" {
  name            = "${var.project_name}-subscription-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.subscription_service.arn
  desired_count   = 1

  placement_constraints {
    type = "distinctInstance"
  }

  tags = var.tags
}

resource "aws_ecs_service" "support_service" {
  name            = "${var.project_name}-support-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.support_service.arn
  desired_count   = 1

  placement_constraints {
    type = "distinctInstance"
  }

  tags = var.tags
}