# Design Document

## Overview

This design document outlines the architectural improvements for the SaaS platform infrastructure, focusing on an API Gateway-first approach with proper authentication flow, multi-AZ deployment, and optimized caching strategies while maintaining cost efficiency for testing environments.

## Architecture

### High-Level Architecture Flow

```
User → API Gateway → Lambda Authorizer → API Gateway → VPC Link → ECS Services → Cache Layer → Database Layer
```

### Core Components

1. **API Gateway (Regional)**: Single entry point for all services
2. **Lambda Authorizer**: JWT validation using Cognito public keys
3. **ECS Services**: Containerized microservices in private subnets
4. **Caching Layer**: Valkey for RDS, DAX for DynamoDB
5. **Database Layer**: Aurora Serverless v2 + DynamoDB
6. **Authentication**: Cognito User Pool with group-based permissions

## Components and Interfaces

### API Gateway Configuration

**Design Decision**: Remove ALB entirely and use API Gateway with VPC Links for direct service access.

- **Regional API Gateway** with custom domain support (production consideration)
- **VPC Links** connecting to individual ECS services on specific ports
- **Lambda REQUEST Authorizer** for JWT validation
- **CORS Configuration** for frontend integration
- **Throttling and Rate Limiting** per endpoint

**Interface Design**:
```
GET  /                          → Frontend (static content)
POST /api/auth/signup          → Subscription Service
POST /api/auth/login           → Cognito Hosted UI redirect
GET  /api/subscription/status  → Subscription Service
POST /api/subscription/update  → Subscription Service
GET  /api/support/tickets      → Support Service
POST /api/support/tickets      → Support Service
```

### Authentication & Authorization

**Lambda Authorizer Design**:
- Validates JWT tokens using Cognito's JWKS endpoint
- Extracts user context (user_id, tenant_id, groups)
- Returns IAM policy with appropriate permissions
- Caches validation results for performance

**JWT Token Structure**:
```json
{
  "sub": "user-uuid",
  "cognito:username": "user@example.com",
  "cognito:groups": ["admin"],
  "email": "user@example.com",
  "tenant_id": "tenant-uuid",
  "exp": 1234567890
}
```

### ECS Service Architecture

**Subscription Service** (Port 5000):
- Handles user registration and Cognito integration
- Manages subscription plans and billing
- Checks membership status and permissions
- Uses Valkey cache for session data and frequent queries
- Connects to Aurora via RDS Proxy

**Support Service** (Port 5001):
- Manages support tickets with tenant isolation
- Uses DynamoDB with DAX for microsecond latency
- Implements proper partition key strategy (tenant_id)
- Handles ticket lifecycle management

**Frontend Service** (Port 5002):
- Serves static web application
- Handles OAuth callback flows
- Integrates with Cognito Hosted UI
- Provides responsive dashboard interface

### Container Images Strategy

**Subscription Service Dockerfile**:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

**Support Service Dockerfile**:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install boto3 flask PyJWT
COPY . .
EXPOSE 5001
CMD ["python", "app.py"]
```

## Data Models

### Aurora PostgreSQL Schema

```sql
-- Tenants table
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR(255) NOT NULL,
    plan VARCHAR(50) NOT NULL CHECK (plan IN ('basic', 'pro', 'enterprise')),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users table (synced with Cognito)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cognito_user_id VARCHAR(255) UNIQUE NOT NULL,
    tenant_id UUID REFERENCES tenants(id),
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Subscriptions table
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    plan VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    billing_cycle VARCHAR(20) DEFAULT 'monthly',
    amount DECIMAL(10,2) NOT NULL,
    next_billing_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### DynamoDB Schema

**Support Tickets Table**:
```json
{
  "TableName": "saas-platform-support-tickets",
  "KeySchema": [
    {"AttributeName": "tenant_id", "KeyType": "HASH"},
    {"AttributeName": "ticket_id", "KeyType": "RANGE"}
  ],
  "GlobalSecondaryIndexes": [
    {
      "IndexName": "status-index",
      "KeySchema": [{"AttributeName": "status", "KeyType": "HASH"}]
    }
  ]
}
```

## Error Handling

### API Gateway Error Responses
- **401 Unauthorized**: Invalid or missing JWT token
- **403 Forbidden**: Valid token but insufficient permissions
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Service unavailable

### Service-Level Error Handling
- Circuit breaker pattern for database connections
- Graceful degradation when cache is unavailable
- Proper logging with correlation IDs
- Health check endpoints for all services

### Database Error Handling
- Connection pooling through RDS Proxy
- Automatic retry logic with exponential backoff
- Fallback to read replicas for read operations
- Transaction rollback on failures

## Testing Strategy

### Unit Testing
- Lambda authorizer JWT validation logic
- Service business logic with mocked dependencies
- Database query functions with test data
- Cache integration with mock Redis/DAX

### Integration Testing
- API Gateway to service communication
- Authentication flow end-to-end
- Database operations with real connections
- Cache hit/miss scenarios

### Load Testing
- API Gateway throttling limits
- ECS auto-scaling triggers
- Database connection pooling
- Cache performance under load

## Multi-AZ Deployment Strategy

### Network Architecture
```
Region: eu-west-2
├── AZ: eu-west-2a
│   ├── Public Subnet: 10.0.1.0/24
│   └── Private Subnet: 10.0.2.0/24
└── AZ: eu-west-2b
    ├── Public Subnet: 10.0.3.0/24
    └── Private Subnet: 10.0.4.0/24
```

### Service Distribution
- **ECS Services**: Distributed across both AZs with auto-scaling
- **Aurora Cluster**: Multi-AZ with automatic failover
- **ElastiCache**: Multi-AZ with replica nodes
- **DynamoDB**: Automatically distributed (managed service)

### Cost Optimization Notes
- Use t3.micro instances for ECS (burstable performance)
- Aurora Serverless v2 with 0.5-1 ACU scaling
- DynamoDB on-demand pricing
- Single NAT Gateway with VPC endpoints where possible

## Production Considerations (Not Implemented)

### Multi-Region Architecture
- **Route 53**: DNS failover between regions
- **CloudFront**: Global CDN with edge caching
- **DynamoDB Global Tables**: Multi-region replication
- **S3 Cross-Region Replication**: For static assets

### Enhanced Security (Production)
- **AWS Shield Advanced**: DDoS protection ($3,000/month - not implemented)
- **WAF Rate Limiting**: Advanced rules and IP blocking
- **VPC Flow Logs**: Network traffic monitoring
- **GuardDuty**: Threat detection and monitoring

### Advanced Monitoring (Production)
- **X-Ray Tracing**: Distributed request tracing
- **Enhanced CloudWatch**: Custom metrics and dashboards
- **AWS Config**: Compliance and configuration monitoring
- **CloudTrail**: Comprehensive API logging

### Certificate and DNS Management (Production)
- **ACM Certificates**: SSL/TLS for custom domains
- **Route 53**: DNS management and health checks
- **Custom Domain**: Branded API endpoints

## Implementation Notes

### Database Migration Strategy
1. Create migration scripts in `migrations/` directory
2. Run migrations through ECS task on deployment
3. Use database versioning for schema changes
4. Implement rollback procedures for failed migrations

### Caching Strategy
- **Valkey (RDS)**: User sessions, subscription data, frequently accessed queries
- **DAX (DynamoDB)**: Support ticket queries, real-time data access
- **TTL Configuration**: 15 minutes for session data, 5 minutes for subscription data

### Monitoring and Alerting
- **CloudWatch Alarms**: CPU > 80%, Memory > 85%, Error rate > 5%
- **SNS Notifications**: Email alerts for critical issues
- **Dashboard Metrics**: Request latency, error rates, cache hit ratios
- **Log Aggregation**: Centralized logging with structured JSON format