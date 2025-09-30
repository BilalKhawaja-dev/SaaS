terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = var.tags
  }
}

# Networking Module
module "networking" {
  source = "./modules/networking"

  project_name        = var.project_name
  region             = var.region
  availability_zone  = var.availability_zone
  vpc_cidr          = var.vpc_cidr
  public_subnet_cidr = var.public_subnet_cidr
  private_subnet_cidr = var.private_subnet_cidr
  tags              = var.tags
}

# Security Module
module "security" {
  source = "./modules/security"

  project_name = var.project_name
  tags        = var.tags
}

# Database Module
module "database" {
  source = "./modules/database"

  project_name           = var.project_name
  vpc_id                = module.networking.vpc_id
  private_subnet_id     = module.networking.private_subnet_id
  rds_security_group_id = module.networking.rds_security_group_id
  db_username           = var.db_username
  rds_instance_class    = var.rds_instance_class
  tags                  = var.tags
}

# Cache Module
module "cache" {
  source = "./modules/cache"

  project_name                 = var.project_name
  private_subnet_id           = module.networking.private_subnet_id
  elasticache_security_group_id = module.networking.elasticache_security_group_id
  elasticache_node_type       = var.elasticache_node_type
  tags                        = var.tags
}

# Storage Module
module "storage" {
  source = "./modules/storage"

  project_name = var.project_name
  tags        = var.tags
}

# Auth Module (without API Gateway domain first)
module "auth" {
  source = "./modules/auth"

  project_name       = var.project_name
  api_gateway_domain = "placeholder.execute-api.${var.region}.amazonaws.com"
  tags              = var.tags
}

# API Module
module "api" {
  source = "./modules/api"

  project_name              = var.project_name
  lambda_execution_role_arn = module.security.lambda_execution_role_arn
  user_pool_id             = module.auth.user_pool_id
  user_pool_client_id      = module.auth.user_pool_client_id
  alb_arn                  = module.compute.alb_arn
  alb_dns_name             = module.compute.alb_dns_name
  tags                     = var.tags
}

# Compute Module
module "compute" {
  source = "./modules/compute"

  project_name           = var.project_name
  vpc_id                = module.networking.vpc_id
  public_subnet_id      = module.networking.public_subnet_id
  private_subnet_id     = module.networking.private_subnet_id
  alb_security_group_id = module.networking.alb_security_group_id
  ecs_security_group_id = module.networking.ecs_security_group_id
  ecs_instance_type     = var.ecs_instance_type
  ecs_task_role_arn     = module.security.ecs_task_role_arn
  ecs_execution_role_arn = module.security.ecs_execution_role_arn
  ecs_instance_profile_name = module.security.ecs_instance_profile_name
  log_group_name        = module.monitoring.app_log_group_name
  tags                  = var.tags
}

# Monitoring Module
module "monitoring" {
  source = "./modules/monitoring"

  project_name = var.project_name
  tags        = var.tags
}

# Notifications Module
module "notifications" {
  source = "./modules/notifications"

  project_name       = var.project_name
  notification_email = var.notification_email
  db_instance_id     = module.database.rds_instance_id
  ecs_service_name   = "${var.project_name}-frontend"
  ecs_cluster_name   = module.compute.ecs_cluster_name
  tags              = var.tags
}