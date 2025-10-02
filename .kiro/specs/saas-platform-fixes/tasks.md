# Implementation Plan

- [x] 1. Fix VPC and networking configuration for multi-AZ deployment
  - Update networking module to support multiple availability zones (eu-west-2a, eu-west-2b)
  - Add second public and private subnets for multi-AZ support
  - Fix VPC ID passing between modules in main.tf
  - Update security groups for proper service communication
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 4.1, 4.2_

- [x] 2. Remove ALB and update compute module for API Gateway-first architecture
  - Remove ALB, target groups, and listeners from compute module
  - Update ECS services to run without load balancer integration
  - Modify auto-scaling policies to use ECS service metrics instead of ALB
  - Update security groups to allow API Gateway VPC Link access
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 3. Fix Lambda authorizer for proper JWT validation
  - Rewrite authorizer.py to use Cognito JWKS endpoint for token validation
  - Fix environment variable passing in Lambda function configuration
  - Implement proper IAM policy generation based on user groups
  - Add error handling and logging for authorization failures
  - Create authorizer deployment package with required dependencies
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

- [x] 4. Update API Gateway configuration to remove ALB dependencies
  - Remove ALB references from API Gateway VPC Link configuration
  - Create individual VPC Links for each ECS service
  - Update API Gateway integrations to point directly to ECS services
  - Configure proper CORS and throttling settings
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 5. Create proper Docker images and update ECS task definitions
  - Create Dockerfile for subscription service with PostgreSQL and caching dependencies
  - Create Dockerfile for support service with DynamoDB SDK
  - Update ECS task definitions to use proper container images instead of inline commands
  - Configure proper health check endpoints for all services
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 6. Implement subscription service for RDS operations
  - Create subscription service application code for user registration and management
  - Implement Cognito integration for user creation and authentication
  - Add subscription plan management and membership status checking
  - Integrate Valkey caching for session data and frequent queries
  - Create proper database connection handling with RDS Proxy
  - _Requirements: 8.2, 5.2, 7.3_

- [x] 7. Update support service for proper DynamoDB integration
  - Rewrite support service to use proper DynamoDB SDK configuration
  - Implement DAX integration for microsecond latency caching
  - Fix tenant isolation using proper partition key strategy
  - Add proper error handling and retry logic
  - _Requirements: 8.3, 5.1, 3.1_

- [x] 8. Fix database module for multi-AZ and proper initialization
  - Update RDS configuration for multi-AZ deployment
  - Fix VPC ID reference in database module variables and main.tf
  - Create proper database migration scripts instead of inline initialization
  - Configure DAX cluster for DynamoDB acceleration
  - Update ElastiCache configuration for multi-AZ support
  - _Requirements: 4.2, 6.1, 5.3, 5.4, 4.4_

- [x] 9. Update Cognito configuration and fix user management
  - Fix demo user creation to match application user structure
  - Ensure JWT tokens contain proper group memberships and tenant information
  - Update Cognito User Pool configuration for proper integration
  - Fix password policies and user group assignments
  - _Requirements: 7.1, 7.2, 7.4, 7.5_

- [x] 10. Implement consistent JWT handling across all services
  - Create shared JWT validation logic for all application services
  - Fix JWT secret management using AWS Secrets Manager
  - Update all services to use consistent token validation
  - Implement proper user context extraction from JWT tokens
  - _Requirements: 2.6, 8.1_

- [x] 11. Configure caching layers (Valkey and DAX)
  - Update cache module to use Valkey instead of Redis
  - Configure DAX cluster for DynamoDB with proper security groups
  - Implement cache integration in subscription service for RDS data
  - Configure cache TTL and eviction policies
  - _Requirements: 5.1, 5.2, 5.5_

- [x] 12. Update frontend service and API Gateway integration
  - Create proper frontend service to serve static content through API Gateway
  - Update frontend HTML to work with new API endpoints
  - Configure API Gateway to serve frontend content
  - Fix OAuth callback handling for Cognito integration
  - _Requirements: 1.3, 3.3, 8.1_

- [x] 13. Update main.tf module dependencies and variable passing
  - Fix all module variable passing, especially VPC ID references
  - Update module dependencies to ensure proper creation order
  - Add missing variables for multi-AZ subnet configuration
  - Update outputs to reflect new architecture without ALB
  - _Requirements: 6.1, 6.2_

- [x] 14. Create database migration system
  - Create migration scripts directory structure
  - Implement database schema creation scripts
  - Create ECS task for running migrations on deployment
  - Add proper error handling and rollback procedures
  - _Requirements: 5.3, 8.4_

- [x] 15. Update monitoring and alerting for new architecture
  - Remove ALB-related CloudWatch alarms
  - Add API Gateway and ECS service monitoring
  - Update SNS notifications for new service architecture
  - Configure proper health checks for all services
  - _Requirements: 3.4, 8.1_

- [x] 16. Update documentation and deployment scripts
  - Update README.md to reflect API Gateway-first architecture
  - Add multi-region production considerations
  - Update deployment scripts for new service structure
  - Add cost optimization notes and production upgrade path
  - _Requirements: 4.5_