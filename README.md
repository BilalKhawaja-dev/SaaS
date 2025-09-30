# Multi-Tenant SaaS Platform - Terraform Infrastructure

## Architecture Overview

This Terraform project implements a cost-optimized multi-tenant SaaS platform for testing purposes, deployed in EU-West-2.

### Domain & SSL Workaround
**No domain or ACM certificate required!** 
- Uses Application Load Balancer with HTTP (port 80)
- Access via ALB DNS name (e.g., `saas-platform-alb-123456789.eu-west-2.elb.amazonaws.com`)
- API Gateway provides additional endpoint for API access

### Authentication
- **Amazon Cognito User Pool** with hosted UI
- **Lambda REQUEST authorizer** validates JWT tokens with group-based permissions
- **User Groups**: admin (full access), user (read-only), readonly (read-only)
- **Demo Accounts**:
  - admin@demo.com / admin123 (admin group)
  - user@demo.com / user123 (user group) 
  - readonly@demo.com / readonly123 (readonly group)
- **OAuth 2.0 flows** via Cognito Hosted UI
- **JWT tokens** with group claims for fine-grained access control

### Current Implementation (Cost-Optimized for Testing)
- Single AZ deployment in eu-west-2a
- Basic tenant isolation (logical only)
- Minimal resource sizing
- **Aurora Serverless v2** with RDS Proxy
- **DAX** for DynamoDB acceleration
- **Valkey 8.0** cache (not Redis)
- **S3 with Macie** for data classification
- **Athena** for analytics queries
- **Auto-scaling** (90% CPU threshold)
- **CloudWatch Dashboard** with comprehensive metrics
- **CodeBuild CI/CD** pipeline with S3 backend
- Email notifications to bilalkwj@amazon.com

### Authentication Flow
```
User → Cognito Hosted UI → JWT Token → API Gateway → Lambda Authorizer → VPC Link → ALB → ECS
```

1. **User accesses application** → Redirected to Cognito Hosted UI
2. **User authenticates** → Cognito issues JWT token with group claims
3. **API requests** → Lambda authorizer validates JWT and checks group permissions
4. **Admin users** → Full access to all endpoints
5. **User/Readonly** → Only GET requests allowed

### Production Considerations (Not Implemented)
For production deployment, consider:
- **Custom domain with ACM certificate** for HTTPS
- **Route 53** for DNS management
- **CloudFront** for global content delivery
- **Aurora read replicas** for read scaling
- **Multi-AZ deployment** for high availability
- **2FA/MFA** for enhanced security
- **SSO integration** (SAML, OIDC) with Cognito Identity Providers
- **Amazon Bedrock** integration for AI-powered analytics (cost consideration)
- **WAF** for application security
- **Enhanced monitoring** with X-Ray tracing
- Multi-AZ deployment across eu-west-2a, eu-west-2b, eu-west-2c
- Aurora with read replicas
- Enhanced tenant isolation with placement groups
- WAF and Shield protection
- Multi-region disaster recovery
- Advanced monitoring and alerting
- Blue-green deployment pipeline

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

### Auth Service (Port 5000)
- User registration and login
- JWT token generation
- Tenant management
- Database initialization with demo data

### Balance Service (Port 5001)
- Account balance management
- Transaction history
- Tenant-specific data isolation

### Support Service (Port 5002)
- Support ticket creation and management
- DynamoDB-based storage
- Ticket status tracking

## API Endpoints

### Authentication
- `POST /api/auth/signup` - Create new account
- `POST /api/auth/login` - User login

### Balance Management
- `GET /api/balance` - Get account balance (requires auth)
- `GET /api/balance/transactions` - Get transaction history (requires auth)

### Support Tickets
- `GET /api/support/tickets` - List tickets (requires auth)
- `POST /api/support/tickets` - Create ticket (requires auth)
- `PUT /api/support/tickets/{id}/status` - Update ticket status (requires auth)

## Database Schema

### PostgreSQL (RDS)
- **tenants**: Company information and plans
- **users**: User accounts with tenant association
- **accounts**: Account balances per tenant
- **transactions**: Transaction history

### DynamoDB
- **support-tickets**: Support ticket storage with tenant isolation

## Security Features

- Database passwords stored in AWS Secrets Manager
- Configuration parameters in SSM Parameter Store
- IAM roles with least privilege access
- Security groups with minimal required access
- JWT-based authentication
- Tenant data isolation
- Encrypted storage (RDS and DynamoDB)

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

## CloudWatch Dashboard

Comprehensive monitoring dashboard includes:
- ECS Service CPU/Memory utilization
- Aurora cluster metrics (CPU, connections)
- Application Load Balancer metrics (requests, response time)
- Auto Scaling Group CPU utilization

## CI/CD Pipeline

### CodeBuild Setup:
1. **Source**: Upload code to S3 bucket
2. **Build**: Terraform plan/apply via CodeBuild
3. **State**: Stored in S3 with DynamoDB locking
4. **Artifacts**: Build outputs stored in S3

### Pipeline Stages:
1. **Source** → Fetch from S3
2. **Plan** → Terraform plan
3. **Apply** → Terraform apply (manual approval recommended for prod)

## Cleanup

```bash
terraform destroy
```