# Requirements Document

## Introduction

This specification addresses critical architectural and implementation issues in the existing multi-tenant SaaS platform Terraform infrastructure. The goal is to create a properly functioning API Gateway-first architecture with correct authentication flow, proper container images, multi-AZ deployment, and optimized caching strategies.

## Requirements

### Requirement 1: API Gateway-First Architecture

**User Story:** As a platform architect, I want to expose all application services exclusively through API Gateway, so that I have a unified entry point without the complexity of managing load balancers.

#### Acceptance Criteria

1. WHEN the infrastructure is deployed THEN the ALB SHALL be completely removed from the compute module
2. WHEN services need to be accessed THEN API Gateway SHALL be the only entry point using VPC Links to ECS services
3. WHEN the frontend is served THEN it SHALL be served directly through API Gateway integration
4. IF a user accesses the platform THEN they SHALL only interact with API Gateway endpoints

### Requirement 2: Authentication and Authorization Flow

**User Story:** As a security engineer, I want a proper JWT-based authentication flow through Cognito and Lambda authorizer, so that all API requests are properly validated and authorized.

#### Acceptance Criteria

1. WHEN a user authenticates THEN Cognito SHALL issue JWT tokens with proper group claims
2. WHEN API requests are made THEN the Lambda authorizer SHALL validate JWT tokens using Cognito's public keys
3. WHEN token validation occurs THEN the authorizer SHALL extract user context (tenant_id, groups, user_id)
4. IF the user has admin role THEN they SHALL have full access to all endpoints
5. IF the user has user/readonly role THEN they SHALL only access GET endpoints
6. WHEN services validate tokens THEN they SHALL use a consistent JWT secret management approach

### Requirement 3: Container Images and Service Architecture

**User Story:** As a DevOps engineer, I want proper Docker images for each service with appropriate configurations, so that services run reliably and can be easily maintained.

#### Acceptance Criteria

1. WHEN the support service is deployed THEN it SHALL have a proper Docker image with DynamoDB SDK and dependencies
2. WHEN the subscription service is deployed THEN it SHALL have a proper Docker image with PostgreSQL drivers and caching libraries
3. WHEN the frontend is deployed THEN it SHALL be served as a static web application through API Gateway
4. WHEN services start THEN they SHALL have proper health check endpoints
5. IF container images are built THEN they SHALL include all necessary dependencies and configurations

### Requirement 4: Multi-AZ Deployment Strategy

**User Story:** As a reliability engineer, I want the infrastructure deployed across multiple availability zones within a single region, so that the system can handle AZ-level failures while maintaining cost efficiency.

#### Acceptance Criteria

1. WHEN the VPC is created THEN it SHALL span multiple availability zones (eu-west-2a, eu-west-2b)
2. WHEN RDS is deployed THEN it SHALL use Multi-AZ deployment for high availability
3. WHEN ECS services are deployed THEN they SHALL be distributed across multiple AZs
4. WHEN ElastiCache is deployed THEN it SHALL support multi-AZ configuration
5. IF documentation is updated THEN it SHALL mention multi-region considerations for production

### Requirement 5: Database and Caching Strategy

**User Story:** As a performance engineer, I want optimized database access with proper caching layers, so that the application performs well under load while maintaining data consistency.

#### Acceptance Criteria

1. WHEN DynamoDB is accessed THEN DAX SHALL provide microsecond latency caching
2. WHEN RDS is accessed THEN Valkey SHALL cache frequently accessed data (user sessions, subscription info)
3. WHEN the database schema is initialized THEN it SHALL happen through proper migration scripts
4. WHEN services connect to databases THEN they SHALL use connection pooling through RDS Proxy
5. IF cache misses occur THEN the system SHALL gracefully fall back to the primary database

### Requirement 6: VPC and Networking Configuration

**User Story:** As a network engineer, I want proper VPC configuration with correct resource references, so that all services can communicate securely within the private network.

#### Acceptance Criteria

1. WHEN modules reference VPC resources THEN all VPC IDs SHALL be properly passed between modules
2. WHEN security groups are created THEN they SHALL allow appropriate traffic between services
3. WHEN subnets are created THEN they SHALL be properly distributed across multiple AZs
4. WHEN VPC endpoints are configured THEN they SHALL optimize traffic routing and reduce NAT Gateway costs
5. IF services need database access THEN security groups SHALL allow appropriate database ports

### Requirement 7: Cognito Integration and User Management

**User Story:** As an authentication administrator, I want Cognito properly integrated with the application services, so that user authentication and authorization work seamlessly across all components.

#### Acceptance Criteria

1. WHEN demo users are created in Cognito THEN they SHALL match the application's expected user structure
2. WHEN users authenticate through Cognito THEN JWT tokens SHALL contain proper group memberships
3. WHEN the subscription service handles signups THEN it SHALL integrate with Cognito for user creation
4. WHEN user groups are managed THEN they SHALL have appropriate permissions (admin, user, readonly)
5. IF password policies are enforced THEN they SHALL meet security requirements (12+ chars, complexity)

### Requirement 8: Service Flow and Data Management

**User Story:** As an application architect, I want a clear service flow from API Gateway through authentication to application services and databases, so that the system architecture is maintainable and scalable.

#### Acceptance Criteria

1. WHEN a request is made THEN it SHALL flow: User → API Gateway → Lambda Authorizer → API Gateway → ECS Service → Cache → Database
2. WHEN the subscription service operates THEN it SHALL handle user registration, subscription management, and membership status
3. WHEN the support service operates THEN it SHALL manage support tickets with tenant isolation in DynamoDB
4. WHEN caching is implemented THEN Valkey SHALL cache RDS data and DAX SHALL accelerate DynamoDB
5. IF services need to communicate THEN they SHALL use proper service discovery and authentication