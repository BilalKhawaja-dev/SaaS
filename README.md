# Multi-Tenant SaaS Platform - Terraform Infrastructure

## Architecture Overview

This Terraform project implements a **cost-optimized multi-tenant SaaS platform** designed for **testing and development environments**. The architecture prioritizes functionality and learning over production-grade features to maintain reasonable AWS costs while demonstrating key concepts.

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
  - admin@democorp.com / AdminDemo123! (admin group)
  - user@testinc.com / UserDemo123! (user group) 
  - readonly@enterpriseltd.com / ReadonlyDemo123! (readonly group)
- **OAuth 2.0 flows** via Cognito Hosted UI with callback support
- **JWT tokens** with tenant context and group claims for fine-grained access control

### What's Actually Implemented (Cost-Optimized for Testing)

**✅ Core Infrastructure:**
- **API Gateway-first architecture** with VPC Links (no ALB for cost savings)
- **Multi-AZ deployment** across eu-west-2a and eu-west-2b
- **ECS with auto-scaling** (t3.micro instances, 90% CPU threshold)
- **Aurora Serverless v2** with RDS Proxy (minimal ACU for cost control)
- **DynamoDB with DAX** (2-node cluster for acceleration)
- **Valkey caching** (single node, not Redis for cost)
- **Cognito authentication** with JWT validation
- **Lambda authorizer** with proper JWKS validation

**✅ Application Services:**
- **Subscription service** - Full Cognito integration, plan management, billing
- **Support service** - Ticket management with DynamoDB storage
- **Frontend service** - Responsive web interface
- **Database migrations** - Automated schema management
- **SNS notifications** - Intelligent routing based on ticket content

**✅ Security & Monitoring:**
- **WAF with Log4j protection** (CVE-2021-44228)
- **CloudWatch monitoring** with basic dashboards
- **IAM roles** with least privilege
- **Secrets Manager** for database credentials
- **VPC security groups** with minimal required access

## Architecture Decisions

### Compute Layer

**ECS with EC2 Launch Type (vs Fargate)**
- **Why EC2**: ~50% cost savings over Fargate for persistent workloads
- **t3.micro instances**: Burstable performance suitable for testing, $8.76/month vs Fargate's $14.40/month
- **Auto Scaling**: Scales based on CPU utilization (90% threshold) across multiple AZs
- **Trade-off**: More infrastructure management vs cost savings for testing environment

**API Gateway (vs Application Load Balancer)**
- **Why API Gateway**: Eliminates ALB costs (~$16/month), provides managed SSL/TLS termination
- **VPC Links**: Direct connection to ECS services without internet routing
- **Regional endpoint**: Lower latency than edge-optimized for single-region deployment
- **Trade-off**: Less flexibility in routing vs significant cost savings and managed features

### Database Layer

**Aurora Serverless v2 (vs RDS or Aurora Provisioned)**
- **Why Serverless**: Auto-scaling from 0.5-1 ACU, pay only for actual usage
- **Multi-AZ**: High availability without managing read replicas
- **RDS Proxy**: Connection pooling and failover handling for microservices
- **Trade-off**: Slight cold start latency vs dramatic cost savings for variable workloads

**DynamoDB with DAX (vs RDS for everything)**
- **Why DynamoDB**: Perfect for support tickets with tenant-based partition keys
- **DAX acceleration**: Microsecond latency for read-heavy workloads
- **On-demand billing**: Pay per request vs provisioned capacity
- **Trade-off**: NoSQL learning curve vs optimal performance and cost for document storage

### Caching Strategy

**ElastiCache Valkey (vs Redis)**
- **Why Valkey**: Open-source Redis fork, no licensing concerns
- **Single node**: Cost optimization for testing (no replication group)
- **t3.micro**: Minimal cost while providing caching benefits
- **Trade-off**: No high availability vs 70% cost reduction for testing

### Authentication & Authorization

**Cognito User Pool (vs Custom Auth)**
- **Why Cognito**: Managed service eliminates auth infrastructure complexity
- **JWT with JWKS**: Industry standard with automatic key rotation
- **Lambda authorizer**: Centralized authorization logic, caches validation results
- **Trade-off**: AWS vendor lock-in vs zero maintenance overhead and security best practices

**Lambda REQUEST Authorizer (vs Cognito Authorizer)**
- **Why Lambda**: Custom business logic for tenant isolation and group-based permissions
- **JWKS validation**: Validates tokens using Cognito's public keys
- **Caching**: 5-minute TTL reduces Cognito API calls
- **Trade-off**: Custom code maintenance vs flexible authorization logic

### Network Architecture

**Multi-AZ Single Region (vs Multi-Region)**
- **Why Single Region**: 50% cost reduction while maintaining high availability
- **eu-west-2**: Low latency for European users, GDPR compliance
- **Multi-AZ**: Automatic failover across availability zones
- **Trade-off**: No disaster recovery across regions vs significant cost savings

**VPC Endpoints (vs NAT Gateway only)**
- **Why VPC Endpoints**: Reduce NAT Gateway data transfer costs for AWS services
- **S3 and DynamoDB endpoints**: Most cost-effective for high-traffic services
- **Single NAT Gateway**: Shared across AZs for internet access
- **Trade-off**: Slight complexity vs reduced data transfer costs

### Container Strategy

**Docker Multi-Stage Builds**
- **Why Multi-Stage**: Smaller image sizes, faster deployments
- **Python slim base**: Reduced attack surface and faster pulls
- **Dependency optimization**: Only production dependencies in final image
- **Trade-off**: Longer build times vs smaller, more secure runtime images

**Service Separation (vs Monolith)**
- **Why Microservices**: Independent scaling, technology choices, and deployment
- **Domain boundaries**: Subscription, Support, and Frontend as separate concerns
- **Shared utilities**: Common JWT and caching logic in shared modules
- **Trade-off**: Increased complexity vs better scalability and maintainability

### Monitoring & Observability

**CloudWatch Basic (vs Enhanced Monitoring)**
- **Why Basic**: Standard metrics sufficient for testing, enhanced monitoring adds $15-30/month
- **Custom dashboards**: Key metrics without detailed container insights
- **SNS alerting**: Email notifications for critical issues
- **Trade-off**: Less detailed insights vs 80% cost reduction for monitoring

**WAF Basic Rules (vs Advanced Protection)**
- **Why Basic**: AWS managed rules provide essential protection
- **Log4j protection**: Specific rule for CVE-2021-44228 vulnerability
- **Rate limiting**: Basic throttling without advanced bot detection
- **Trade-off**: Less sophisticated attack detection vs core protection at minimal cost

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

### ❌ What's NOT Implemented (Cost & Complexity Considerations)

**Excluded for Cost Reasons:**
- **CloudFront CDN** - Would add ~$20-50/month for global distribution
- **Route 53 hosted zones** - $0.50/zone/month + query costs
- **AWS Shield Advanced** - $3,000/month for DDoS protection
- **Multi-region deployment** - Would double infrastructure costs
- **Enhanced monitoring** - X-Ray tracing, detailed CloudWatch metrics
- **Custom domains/SSL** - ACM certificates and domain management
- **VPC Flow Logs** - Additional storage and analysis costs
- **GuardDuty** - $4.60/million events for threat detection
- **Config compliance** - $0.003/configuration item recorded

**Excluded for Testing Simplicity:**
- **Blue-green deployments** - Complex CI/CD pipeline setup
- **Advanced auto-scaling** - Predictive scaling, multiple metrics
- **Cross-region replication** - DynamoDB Global Tables, S3 CRR
- **Enterprise SSO** - SAML/OIDC integration complexity
- **Advanced tenant isolation** - Dedicated instances, placement groups
- **Comprehensive backup** - Cross-region snapshots, point-in-time recovery

**Production Upgrade Path:**
This architecture is designed to easily scale to production by:
1. Adding CloudFront for global distribution
2. Implementing Route 53 for DNS management
3. Enabling cross-region replication
4. Adding comprehensive monitoring and alerting
5. Implementing blue-green deployment pipelines
6. Enhancing security with Shield Advanced and GuardDuty

**Current Cost Target:** ~$50-80/month for testing workloads

## Deployed Services

**Core Infrastructure:**
- **Networking**: Multi-AZ VPC with public/private subnets, security groups
- **Compute**: ECS cluster with auto-scaling EC2 instances (t3.micro)
- **API Gateway**: Regional endpoint with VPC Links (no ALB)
- **Authentication**: Cognito User Pool with Lambda authorizer

**Data Layer:**
- **Aurora Serverless v2**: PostgreSQL with RDS Proxy connection pooling
- **DynamoDB**: Support tickets and sessions with DAX acceleration
- **ElastiCache**: Valkey 8.0 for subscription data caching
- **S3**: Asset storage and logging buckets

**Application Services:**
- **Subscription Service**: User registration, plan management, billing
- **Support Service**: Ticket management with tenant isolation
- **Frontend Service**: Responsive web interface with OAuth integration

**Operations:**
- **CloudWatch**: Basic monitoring and alerting
- **SNS**: Intelligent notification routing
- **Secrets Manager**: Database credential management
- **WAF**: Basic protection with Log4j rules
- **IAM**: Least-privilege role-based access

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
- **admin@democorp.com** / AdminDemo123! (Admin - full access)
- **user@testinc.com** / UserDemo123! (User - read-only access)
- **readonly@enterpriseltd.com** / ReadonlyDemo123! (Read-only access)

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

## Cost Optimization Strategy

**Instance Sizing (Testing-Optimized):**
- **ECS**: t3.micro instances (burstable performance)
- **Aurora**: Serverless v2 with 0.5-1 ACU scaling
- **ElastiCache**: Single t3.micro node (no replication for cost)
- **DAX**: 2x dax.t3.small nodes (minimum for cluster)

**Network Cost Savings:**
- **No ALB** - API Gateway handles load balancing
- **Single NAT Gateway** - Shared across AZs
- **VPC Endpoints** - Reduce NAT Gateway usage where possible

**Storage & Monitoring:**
- **DynamoDB**: On-demand pricing (pay per use)
- **S3**: Standard storage class
- **CloudWatch**: Basic retention periods (7 days)
- **No enhanced monitoring** - Standard metrics only

**Estimated Monthly Cost:** $50-80 for light testing workloads

**Cost Breakdown:**
- ECS (t3.micro): ~$15/month
- Aurora Serverless v2: ~$15-25/month
- DynamoDB + DAX: ~$10-15/month
- ElastiCache: ~$10/month
- API Gateway: ~$3-5/month
- Other services: ~$5-10/month

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

## Development Notes

**Architecture Decisions:**
- **API Gateway over ALB**: Reduces costs and complexity while providing managed SSL/HTTPS
- **Aurora Serverless v2**: Auto-scaling database that scales to zero when not in use
- **Single-region deployment**: Multi-AZ for availability, single region for cost control
- **Minimal monitoring**: Basic CloudWatch metrics without enhanced monitoring costs

**Key Learnings:**
- **Resource naming limits**: AWS services have strict naming constraints (DAX clusters: 20 chars max)
- **Cost vs. features trade-offs**: Production features can easily 10x infrastructure costs
- **Multi-tenant complexity**: Proper tenant isolation requires careful data modeling
- **Authentication flows**: JWT validation with Cognito requires proper JWKS handling

**Testing Approach:**
- **Infrastructure as Code**: All resources defined in Terraform for reproducibility
- **Modular design**: Separate modules for easy component testing and replacement
- **Cost monitoring**: Regular cost analysis to stay within testing budget
- **Incremental deployment**: Build and test components individually before integration

## Cleanup

```bash
terraform destroy
```

**Note**: Destroy will remove all resources and data. Ensure you have backups if needed.
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