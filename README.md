# Multi-Tenant SaaS Platform - Terraform Infrastructure

## Architecture Overview

This Terraform project implements a cost-optimized multi-tenant SaaS platform for testing purposes, deployed across multiple availability zones in EU-West-2 for high availability.

### Architecture & Access
**API Gateway-First Architecture** 
- **No ALB** - Applications exposed exclusively via API Gateway with VPC Links
- **Network Load Balancer** - Internal NLB for VPC Link connectivity to ECS services
- **SSL/TLS termination** - API Gateway handles HTTPS with regional endpoints
- **Direct service access** - API Gateway connects to individual ECS services on dedicated ports
- Access via API Gateway URL (e.g., `https://abc123.execute-api.eu-west-2.amazonaws.com/dev`)

### Authentication & Authorization
- **Amazon Cognito User Pool** with enhanced security (12+ char passwords, complexity required)
- **Lambda REQUEST authorizer** validates JWT tokens using Cognito JWKS endpoint
- **Custom token attributes** - Tenant ID and company name embedded in JWT tokens
- **User Groups**: admin (full access), user (read-only), readonly (read-only)
- **Demo Accounts**:
  - admin@democorp.com / Admin123! (admin group)
  - user@testinc.com / User123! (user group) 
  - readonly@enterpriseltd.com / Readonly123! (readonly group)
- **OAuth 2.0 flows** via Cognito Hosted UI with callback support
- **JWT tokens** with tenant context and group claims for fine-grained access control

### Current Implementation (Multi-AZ, Cost-Optimized for Testing)
- **Multi-AZ deployment** across eu-west-2a and eu-west-2b (high availability)
- **Aurora Serverless v2** with Multi-AZ instances and RDS Proxy connection pooling
- **DAX cluster** with 2 nodes for DynamoDB acceleration and failover
- **Valkey 8.0 replication group** with automatic failover (not Redis)
- **S3 with Macie** for data classification and PII detection
- **Athena** for analytics queries on S3 data lake
- **Auto-scaling** (90% CPU threshold) across multiple AZs
- **WAF** with AWS managed rules + Log4j protection (CVE-2021-44228)
- **CloudTrail & Config** with CloudWatch Logs
- **Enterprise CloudWatch Dashboard** with comprehensive metrics
- **CodeBuild CI/CD** with blue-green deployment capability
- **Database migrations** with automated schema management
- **Complete subscription service** with Cognito integration and RDS operations
- **Intelligent SNS notifications** with Lambda-based routing for support tickets
- **Multi-team email routing** based on ticket content and priority

### Authentication Flow
```
User → Cognito Hosted UI → JWT Token → API Gateway → Lambda Authorizer → VPC Link → NLB → ECS Services
```

1. **User accesses application** → Redirected to Cognito Hosted UI
2. **User authenticates** → Cognito issues JWT token with tenant context and group claims
3. **API requests** → Lambda authorizer validates JWT using Cognito JWKS and checks permissions
4. **Admin users** → Full access to all endpoints across all services
5. **User/Readonly** → Only GET requests allowed with tenant isolation
6. **Service routing** → API Gateway routes to appropriate ECS service via NLB target groups

### Architecture Decoupling & High Availability
- **Aurora Serverless v2** auto-scales compute (0.5-1 ACU) with Multi-AZ instances
- **RDS Proxy** handles connection pooling, failover, and load balancing
- **API Gateway Regional** provides managed endpoint with built-in redundancy
- **ECS Auto Scaling** responds to 90% CPU threshold across multiple AZs
- **Multiple ECS services** (subscription, support, frontend) with service isolation
- **DAX cluster** provides microsecond DynamoDB latency with 2-node failover
- **Valkey replication group** with automatic failover and read replicas
- **Network Load Balancer** distributes traffic across healthy ECS instances

### Backup & Disaster Recovery (Production Recommendations)
- **Aurora automated backups** (7-day retention configured)
- **Point-in-time recovery** available for Aurora
- **S3 versioning** enabled for all buckets
- **Cross-region replication** for critical S3 buckets
- **Database snapshots** before major deployments
- **Infrastructure as Code** enables rapid environment recreation

### Production Considerations (Not Implemented - Cost Optimization)
For production deployment, consider these additional features:

**Multi-Region Architecture:**
- **Route 53** for DNS management and health checks with failover routing
- **CloudFront** for global content delivery, edge caching, and DDoS protection
- **Cross-region Aurora read replicas** for read scaling and disaster recovery
- **DynamoDB Global Tables** for multi-region data replication
- **S3 Cross-Region Replication** for critical data backup

**Enhanced Security (Production Only):**
- **AWS Shield Advanced** ($3,000/month - DDoS protection with 24/7 support)
- **Custom domain with ACM certificate** for branded API endpoints
- **2FA/MFA** integration with Cognito for enhanced user security
- **SSO integration** (SAML, OIDC) with enterprise identity providers
- **VPC Flow Logs** for network traffic monitoring and security analysis
- **GuardDuty** for threat detection and security monitoring

**Advanced Features:**
- **Amazon Bedrock** integration for AI-powered analytics (cost consideration)
- **X-Ray tracing** for distributed request tracing and performance analysis
- **Enhanced CloudWatch** with custom metrics and detailed monitoring
- **AWS Config** for compliance monitoring and configuration management
- **Enhanced tenant isolation** with ECS placement groups and dedicated instances
- **Blue-green deployment pipeline** with automated rollback capabilities

**Why Not Implemented:**
These features significantly increase costs and complexity. For testing/development environments, the current multi-AZ setup provides sufficient reliability while maintaining cost efficiency. The architecture is designed to easily scale to these production features when needed.

## Services Deployed

- **Networking**: VPC, subnets, security groups
- **Compute**: ECS cluster with EC2 instances
- **Database**: RDS PostgreSQL for relational data, DynamoDB for unstructured data
- **Authentication**: Cognito User Pool
- **API**: API Gateway with Lambda authorizer
- **Database**: Aurora Serverless v2 with RDS Proxy
- **Caching**: ElastiCache Valkey 8.0 + DAX for DynamoDB
- **Storage**: S3 buckets with Macie classification
- **Analytics**: Athena for querying S3 data lake
- **Monitoring**: CloudWatch Dashboard with comprehensive metrics
- **Auto-scaling**: EC2 Auto Scaling (90% CPU trigger)
- **Notifications**: SNS topic with email alerts
- **CI/CD**: CodeBuild pipeline with S3 backend
- **Security**: IAM roles, Secrets Manager, Macie

## Module Structure

```
modules/
├── networking/     # VPC, subnets, security groups
├── compute/        # ECS cluster and services
├── database/       # RDS and DynamoDB
├── auth/          # Cognito and Lambda authorizer
├── api/           # API Gateway
├── cache/         # ElastiCache
├── storage/       # S3 buckets
├── monitoring/    # CloudWatch
└── security/      # IAM roles and policies
```

## Deployment

### Quick Start
```bash
./deploy.sh
```

### Manual Deployment
1. Copy `terraform.tfvars.example` to `terraform.tfvars`
2. Update variables as needed
3. Run:
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

## Demo Accounts

After deployment, access the Cognito Hosted UI and use these accounts:
- **admin@demo.com** / admin123 (Admin - full access)
- **user@demo.com** / user123 (User - read-only access)
- **readonly@demo.com** / readonly123 (Read-only access)

**Cognito Hosted UI URL**: Available in Terraform outputs after deployment

## Services

### Frontend
- Beautiful responsive web interface
- User authentication and signup
- Service dashboards for balance and support tickets

### Subscription Service (Port 5000) ✅ **FULLY IMPLEMENTED**
- **Complete Cognito Integration**: User registration creates accounts in both Cognito and local database
- **Multi-tenant Architecture**: Proper tenant isolation with custom JWT attributes
- **Subscription Management**: Full lifecycle management (Basic $29, Pro $99, Enterprise $299)
- **RDS Operations**: Aurora Serverless v2 with RDS Proxy connection pooling
- **Valkey Caching**: Intelligent caching for subscription data and account balances
- **Transaction Logging**: Complete audit trail for plan changes and billing events
- **Account Balance Management**: Real-time balance tracking with cached responses
- **Demo Data**: Automatic initialization of demo tenants and subscriptions

### Support Service (Port 5001)
- Support ticket creation and management
- DynamoDB-based storage with tenant isolation
- DAX acceleration for microsecond query latency
- Ticket lifecycle management (open, in_progress, resolved, closed)
- Priority-based ticket handling

### Frontend Service (Port 5002)
- Responsive web application interface
- Cognito Hosted UI integration
- Service dashboards for subscription and support
- OAuth callback handling

## API Endpoints

### Subscription Management ✅ **COMPLETE API**
- `POST /api/subscription/signup` - Create new account with Cognito integration (no auth)
- `GET /api/subscription/status` - Get subscription and account balance (requires auth)
- `PUT /api/subscription/update` - Update subscription plan with transaction logging (requires auth)
- `GET /api/subscription/billing` - Get complete billing history and transactions (requires auth)
- `GET /api/subscription/balance` - Get real-time account balance (requires auth)

### Support Tickets
- `GET /api/support/tickets` - List tickets for tenant (requires auth)
- `POST /api/support/tickets` - Create new ticket (requires auth)
- `GET /api/support/tickets/{id}` - Get specific ticket (requires auth)
- `PUT /api/support/tickets/{id}/status` - Update ticket status (requires auth)
- `PUT /api/support/tickets/{id}` - Update ticket details (requires auth)
- `DELETE /api/support/tickets/{id}` - Delete ticket (requires auth)

### Frontend
- `GET /` - Serve web application (no auth)
- OAuth callbacks handled by Cognito integration

## Database Schema

### PostgreSQL (Aurora Serverless v2)
- **tenants**: Company information, plans, and status
- **users**: User accounts with tenant association and Cognito integration
- **subscriptions**: Subscription plans, billing cycles, and payment information
- **accounts**: Account balances and financial data per tenant
- **transactions**: Transaction history with type classification

### DynamoDB (with DAX Acceleration)
- **support-tickets**: Support ticket storage with tenant isolation using partition keys
- **user-sessions**: User session data for caching (TTL enabled)

## Security Features

- **Enhanced Password Policy**: 12+ characters with complexity requirements
- **Log4j Protection**: WAF blocks ${jndi: lookup attempts (CVE-2021-44228)
- **Least Privilege IAM**: Specific service permissions with no wildcard access
- **JWT Secret Management**: Centralized JWT secrets in AWS Secrets Manager
- **Cognito JWKS Validation**: Lambda authorizer uses Cognito's public keys for token validation
- **Tenant Data Isolation**: Partition keys and row-level security for multi-tenant data
- **Database Security**: Passwords in Secrets Manager, RDS Proxy connection pooling
- **Configuration Security**: SSM Parameter Store for service configuration
- **Network Security**: Security groups with minimal required access, private subnets
- **Encryption**: At-rest encryption for RDS, DynamoDB, and S3
- **API Security**: Request validation, throttling, and CORS configuration

## Cost Optimization Notes

- Uses t3.micro instances for ECS
- Single RDS db.t3.micro instance
- DynamoDB on-demand (pay per use)
- ElastiCache t3.micro node
- No NAT Gateway (uses VPC endpoints where possible)
- Minimal CloudWatch retention periods

## Estimated Monthly Cost
Approximately $50-80/month for basic testing workload.

## Accessing the Application

After deployment:
1. Get the ALB DNS name from Terraform outputs
2. Access the application via the ALB URL
3. Sign up for a new account or use demo credentials
4. Explore the balance and support ticket features

## Notifications

Email notifications are sent to `bilalkwj@amazon.com` for:
- RDS CPU utilization > 80%
- ECS service task count < 1 (service down)

**Note**: You'll need to confirm the SNS email subscription after deployment.

## Auto-Scaling

- **Trigger**: 90% CPU utilization for 2 consecutive periods (5 minutes each)
- **Scale Up**: Add 1 instance when CPU > 90%
- **Scale Down**: Remove 1 instance when CPU < 20%
- **Min Instances**: 1
- **Max Instances**: 5

## Enterprise CloudWatch Dashboard

**Comprehensive multi-service monitoring** across all platform components:
- **API Gateway**: Request count, latency, 4XX/5XX error rates, throttling metrics
- **Application Services**: ECS CPU/Memory utilization, running task counts per service
- **Database**: Aurora CPU, connections, read/write latency, connection pool metrics
- **Infrastructure**: Auto Scaling group metrics, desired vs actual capacity
- **Authentication**: Lambda authorizer duration, invocations, error rates
- **Caching Performance**: Valkey CPU/network metrics, DAX hit/miss ratios
- **Security Monitoring**: WAF allowed/blocked requests, threat detection
- **Data Analytics**: S3 analytics bucket metrics, Athena query performance

**CloudWatch Alarms:**
- API Gateway 4XX/5XX errors and latency thresholds
- Lambda authorizer errors and duration monitoring
- Cache performance (Valkey and DAX CPU utilization)
- ECS service health and auto-scaling triggers
- Database connection and performance monitoring

## CI/CD Pipeline

### CodeBuild Setup:
1. **Source**: Upload code to S3 bucket
2. **Build**: Terraform plan/apply via CodeBuild
3. **State**: Stored in S3 with DynamoDB locking
4. **Artifacts**: Build outputs stored in S3

### Blue-Green Deployment Support:
- **CodeBuild** supports environment variables for target environment
- **ECS services** can be updated with zero-downtime deployments
- **Aurora Serverless** auto-scales without downtime
- **API Gateway** stages enable traffic shifting

### Pipeline Stages:
1. **Source** → Fetch from S3
2. **Plan** → Terraform plan (validation)
3. **Apply** → Terraform apply with blue-green capability

## Cleanup

```bash
terraform destroy
```
#
# 📧 Intelligent SNS Notification System

The platform includes an advanced support ticket notification system that intelligently routes tickets to appropriate teams based on content analysis and priority levels.

### Notification Architecture
```
Support Ticket → Main SNS Topic → Lambda Router → Team-Specific SNS Topics → Email Notifications
```

### Routing Logic
The Lambda function analyzes ticket content using keyword matching and priority levels:

#### 🚨 Urgent Tickets (Priority: urgent)
- **Destination**: bilalkwj@amazon.com
- **Response Time**: Immediate (15 minutes)
- **Triggers**: Any ticket marked as "urgent" priority

#### 🔐 Password/Authentication Issues
- **Destination**: support-password@example.com
- **Keywords**: password, reset, login, authentication, auth, signin, access, locked out, credentials
- **Examples**: "Password reset not working", "Cannot login to account"

#### 💳 Billing/Payment Issues
- **Destination**: billing-support@example.com
- **Keywords**: billing, payment, invoice, charge, subscription, plan, upgrade, refund, credit card
- **Examples**: "Charged twice this month", "Need to update payment method"

#### 🔧 Technical Issues
- **Destination**: tech-support@example.com
- **Keywords**: bug, error, crash, performance, api, database, server, timeout, connection, ssl
- **Examples**: "API returning 500 errors", "Database connection timeouts"

#### 📋 General Support
- **Destination**: general-support@example.com
- **Default**: All tickets that don't match specific categories
- **Examples**: "How to export data", "Feature request"

### Testing the Notification System

1. **Deploy the infrastructure**:
   ```bash
   ./deploy.sh
   ```

2. **Confirm email subscriptions** in all team inboxes

3. **Run the test script**:
   ```bash
   python3 test_notifications.py
   ```

4. **Create test tickets** through the frontend or API:
   ```bash
   curl -X POST https://your-api-gateway-url/api/support/tickets \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "subject": "URGENT: System Down",
       "description": "The entire system is not responding",
       "priority": "urgent"
     }'
   ```

### Monitoring Notifications

- **CloudWatch Logs**: `/aws/lambda/saas-platform-ticket-router`
- **SNS Metrics**: AWS Console → CloudWatch → Metrics → SNS
- **Lambda Metrics**: AWS Console → CloudWatch → Metrics → Lambda

### Customizing Routing

To modify routing logic, update `modules/notifications/ticket_router.py`:

```python
ROUTING_KEYWORDS = {
    'password_reset': ['password', 'reset', 'login', ...],
    'billing': ['billing', 'payment', 'invoice', ...],
    'technical': ['bug', 'error', 'api', ...]
}
```

Then redeploy:
```bash
terraform apply
```