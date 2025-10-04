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

  project_name         = var.project_name
  region              = var.region
  availability_zones  = var.availability_zones
  vpc_cidr           = var.vpc_cidr
  public_subnet_cidrs = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
  tags               = var.tags
}

# Security Module
module "security" {
  source = "./modules/security"

  project_name  = var.project_name
  deployment_id = var.deployment_id
  tags         = var.tags
}

# Database Module
module "database" {
  source = "./modules/database"

  project_name           = var.project_name
  vpc_id                = module.networking.vpc_id
  private_subnet_ids    = module.networking.private_subnet_ids
  rds_security_group_id = module.networking.rds_security_group_id
  db_username           = var.db_username
  rds_instance_class    = var.rds_instance_class
  deployment_id         = var.deployment_id
  tags                  = var.tags
}

# Cache Module
module "cache" {
  source = "./modules/cache"

  project_name                 = var.project_name
  private_subnet_ids          = module.networking.private_subnet_ids
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

# ECR Module
module "ecr" {
  source = "./modules/ecr"

  project_name = var.project_name
  tags        = var.tags
}

# Monitoring Module
module "monitoring" {
  source = "./modules/monitoring"

  project_name = var.project_name
  tags        = var.tags
}

# Notifications Module - Intelligent SNS routing for support tickets
module "notifications" {
  source = "./modules/notifications"

  project_name       = var.project_name
  environment        = var.environment
  vpc_id            = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids

  depends_on = [module.networking]
}

# Auth Module
module "auth" {
  source = "./modules/auth"

  project_name       = var.project_name
  api_gateway_domain = "placeholder.execute-api.${var.region}.amazonaws.com"
  create_demo_users  = true   # Enable demo users for testing
  tags              = var.tags
}

# API Module
module "api" {
  source = "./modules/api"

  project_name              = var.project_name
  vpc_id                   = module.networking.vpc_id
  private_subnet_ids       = module.networking.private_subnet_ids
  lambda_execution_role_arn = module.security.lambda_execution_role_arn
  user_pool_id             = module.auth.user_pool_id
  user_pool_client_id      = module.auth.user_pool_client_id
  tags                     = var.tags

  depends_on = [module.auth, module.security, module.monitoring]
}

# Compute Module
module "compute" {
  source = "./modules/compute"

  project_name           = var.project_name
  vpc_id                = module.networking.vpc_id
  public_subnet_ids     = module.networking.public_subnet_ids
  private_subnet_ids    = module.networking.private_subnet_ids
  ecs_security_group_id = module.networking.ecs_security_group_id
  ecs_instance_type     = var.ecs_instance_type
  ecs_task_role_arn     = module.security.ecs_task_role_arn
  ecs_execution_role_arn = module.security.ecs_execution_role_arn
  ecs_instance_profile_name = module.security.ecs_instance_profile_name
  log_group_name        = module.monitoring.app_log_group_name
  sns_topic_arn         = module.notifications.main_topic_arn
  nlb_target_group_frontend_arn = module.api.nlb_target_group_frontend_arn
  nlb_target_group_subscription_arn = module.api.nlb_target_group_subscription_arn
  nlb_target_group_support_arn = module.api.nlb_target_group_support_arn
  user_pool_id          = module.auth.user_pool_id
  user_pool_client_id   = module.auth.user_pool_client_id
  tags                  = var.tags

  depends_on = [module.api]
}



# CI/CD Module
module "cicd" {
  source = "./modules/cicd"

  project_name         = var.project_name
  source_bucket_name   = module.storage.assets_bucket_name
  artifacts_bucket_name = module.storage.logs_bucket_name
  tags                = var.tags
}

# Security Compliance Module - Disabled due to syntax errors
# module "security_compliance" {
#   source = "./modules/security-compliance"
#
#   project_name           = var.project_name
#   api_gateway_stage_arn  = module.api.api_gateway_stage_arn
#   cloudtrail_bucket_name = module.storage.logs_bucket_name
#   config_bucket_name     = module.storage.logs_bucket_name
#   tags                  = var.tags
# }
# Outputs for SNS notification system
output "main_sns_topic_arn" {
  description = "ARN of the main support tickets SNS topic"
  value       = module.notifications.main_topic_arn
}

output "urgent_sns_topic_arn" {
  description = "ARN of the urgent tickets SNS topic"
  value       = module.notifications.urgent_topic_arn
}

output "lambda_router_arn" {
  description = "ARN of the ticket router Lambda function"
  value       = module.notifications.lambda_function_arn
}