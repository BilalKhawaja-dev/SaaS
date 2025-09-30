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
  vpc_zone_identifier = [var.private_subnet_id]
  min_size            = 1
  max_size            = 5
  desired_capacity    = 1
  
  target_group_arns = [aws_lb_target_group.app.arn]
  health_check_type = "ELB"
  health_check_grace_period = 300

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
  namespace           = "AWS/EC2"
  period              = "300"
  statistic           = "Average"
  threshold           = "90"
  alarm_description   = "This metric monitors ec2 cpu utilization"
  alarm_actions       = [aws_autoscaling_policy.scale_up.arn, var.sns_topic_arn]

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.ecs.name
  }

  tags = var.tags
}

# CloudWatch Alarm - Low CPU
resource "aws_cloudwatch_metric_alarm" "cpu_low" {
  alarm_name          = "${var.project_name}-cpu-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "300"
  statistic           = "Average"
  threshold           = "20"
  alarm_description   = "This metric monitors ec2 cpu utilization"
  alarm_actions       = [aws_autoscaling_policy.scale_down.arn]

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.ecs.name
  }

  tags = var.tags
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [var.alb_security_group_id]
  subnets            = [var.public_subnet_id] # Single AZ for cost

  enable_deletion_protection = false

  tags = var.tags
}

# ALB Target Group
resource "aws_lb_target_group" "app" {
  name     = "${var.project_name}-app-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = var.vpc_id

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  tags = var.tags
}

# ALB Listener
resource "aws_lb_listener" "app" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
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
      name  = "frontend"
      image = "nginx:alpine"
      portMappings = [
        {
          containerPort = 80
          hostPort      = 0
          protocol      = "tcp"
        }
      ]
      essential = true
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

resource "aws_ecs_task_definition" "auth_service" {
  family                   = "${var.project_name}-auth-service"
  network_mode             = "bridge"
  requires_compatibilities = ["EC2"]
  execution_role_arn       = var.ecs_execution_role_arn
  task_role_arn           = var.ecs_task_role_arn

  container_definitions = jsonencode([
    {
      name  = "auth-service"
      image = "python:3.11-slim"
      portMappings = [
        {
          containerPort = 5000
          hostPort      = 0
          protocol      = "tcp"
        }
      ]
      essential = true
      command = [
        "sh", "-c",
        "pip install flask psycopg2-binary boto3 bcrypt PyJWT && python -c 'from flask import Flask; app=Flask(__name__); @app.route(\"/health\"); def health(): return {\"status\": \"healthy\"}; app.run(host=\"0.0.0.0\", port=5000)'"
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = var.log_group_name
          "awslogs-region"        = "eu-west-2"
          "awslogs-stream-prefix" = "auth-service"
        }
      }
    }
  ])

  tags = var.tags
}

resource "aws_ecs_task_definition" "balance_service" {
  family                   = "${var.project_name}-balance-service"
  network_mode             = "bridge"
  requires_compatibilities = ["EC2"]
  execution_role_arn       = var.ecs_execution_role_arn
  task_role_arn           = var.ecs_task_role_arn

  container_definitions = jsonencode([
    {
      name  = "balance-service"
      image = "python:3.11-slim"
      portMappings = [
        {
          containerPort = 5001
          hostPort      = 0
          protocol      = "tcp"
        }
      ]
      essential = true
      command = [
        "sh", "-c",
        "pip install flask psycopg2-binary boto3 PyJWT && python -c 'from flask import Flask; app=Flask(__name__); @app.route(\"/health\"); def health(): return {\"status\": \"healthy\"}; app.run(host=\"0.0.0.0\", port=5001)'"
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = var.log_group_name
          "awslogs-region"        = "eu-west-2"
          "awslogs-stream-prefix" = "balance-service"
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
      name  = "support-service"
      image = "python:3.11-slim"
      portMappings = [
        {
          containerPort = 5002
          hostPort      = 0
          protocol      = "tcp"
        }
      ]
      essential = true
      command = [
        "sh", "-c",
        "pip install flask boto3 PyJWT && python -c 'from flask import Flask; app=Flask(__name__); @app.route(\"/health\"); def health(): return {\"status\": \"healthy\"}; app.run(host=\"0.0.0.0\", port=5002)'"
      ]
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

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "frontend"
    container_port   = 80
  }

  depends_on = [aws_lb_listener.app]

  tags = var.tags
}

resource "aws_ecs_service" "auth_service" {
  name            = "${var.project_name}-auth-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.auth_service.arn
  desired_count   = 1

  tags = var.tags
}

resource "aws_ecs_service" "balance_service" {
  name            = "${var.project_name}-balance-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.balance_service.arn
  desired_count   = 1

  tags = var.tags
}

resource "aws_ecs_service" "support_service" {
  name            = "${var.project_name}-support-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.support_service.arn
  desired_count   = 1

  tags = var.tags
}