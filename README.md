# Multi-Tenant SaaS Platform — Secure by Design on AWS

Terraform-based multi-tenant SaaS platform demonstrating enterprise security patterns: Cognito RBAC with Lambda authorizer, WAF with CVE-specific rules (Log4j), CloudTrail audit logging, AWS Config compliance monitoring, tenant data isolation, Secrets Manager credential management, and least-privilege IAM — all with documented architecture decisions and tradeoffs.

## Architecture

```
Users → API Gateway (TLS) → Lambda Authorizer (JWT/JWKS) → VPC Link → NLB → ECS Services
  ↓                                                                            ↓
Cognito (RBAC)                                                    Aurora Serverless v2 / DynamoDB + DAX
  ↓                                                                            ↓
WAF (OWASP + Log4j)                                              Secrets Manager / Valkey Cache
```

## Security Highlights

### Authentication & Authorization
- Cognito User Pool with enforced password policy (12+ chars, complexity required)
- Lambda REQUEST authorizer validates JWTs using Cognito JWKS public keys (5-min cache TTL)
- JWT tokens carry tenant ID and company name as custom claims
- RBAC via Cognito user groups: admin (full access), user (read-only), readonly
- OAuth 2.0 authorization code flow via Cognito Hosted UI

### Multi-Tenant Data Isolation
- DynamoDB partition keys enforce tenant-level data boundaries
- Row-level security on support tickets — users can only access their tenant's data
- Tenant context embedded in JWT tokens and validated on every request
- Separate database schemas per tenant in Aurora

### WAF & Network Security
- AWS Managed Rules (Common Rule Set) for OWASP top threats
- Custom rule blocking Log4j JNDI lookup attempts (CVE-2021-44228) with URL decode + lowercase transforms
- WAF associated with API Gateway stage
- Multi-AZ VPC with private subnets for databases
- Security groups with minimal required access
- Single NAT Gateway + VPC endpoints for S3/DynamoDB to reduce data transfer costs

### Audit & Compliance
- CloudTrail with CloudWatch Logs integration (30-day retention)
- AWS Config recorder monitoring all resource types
- CloudWatch dashboards covering API Gateway, ECS, Aurora, Lambda authorizer, WAF, DAX
- SNS alerting for critical issues (error rates, latency, service health)

### Secrets & Credential Management
- Database passwords stored in Secrets Manager (never in code or env vars)
- RDS Proxy handles connection pooling and credential rotation
- SSM Parameter Store for non-sensitive service configuration
- No hardcoded credentials anywhere in the codebase

### IAM Least Privilege
- Service-specific IAM roles with no wildcard permissions
- Lambda authorizer role scoped to Cognito JWKS endpoint only
- ECS task roles scoped to specific DynamoDB tables and S3 buckets
- Docker containers run as non-root users


## Infrastructure Components

| Layer | Services | Security Controls |
|-------|----------|-------------------|
| Auth | Cognito, Lambda Authorizer | JWKS validation, RBAC, tenant isolation |
| Network | VPC, NLB, API Gateway | Multi-AZ, private subnets, TLS termination |
| WAF | Web ACL (2 rules) | OWASP managed rules, CVE-2021-44228 block |
| Compute | ECS (EC2 launch type) | Auto-scaling, non-root containers, health checks |
| Relational DB | Aurora Serverless v2 + RDS Proxy | Encryption at rest, connection pooling, 7-day backups |
| NoSQL | DynamoDB + DAX | Tenant-partitioned, encryption, microsecond latency |
| Cache | ElastiCache Valkey | Session and subscription data caching |
| Audit | CloudTrail, AWS Config | API logging, resource compliance monitoring |
| Monitoring | CloudWatch, SNS | Dashboards, alarms, intelligent ticket routing |
| Secrets | Secrets Manager, SSM | Credential management, config separation |
| Storage | S3 | Versioning, encryption, lifecycle policies |
| CI/CD | CodeBuild, CodePipeline | Automated plan/apply, blue-green support |

## Solutions Architect Materials

```
Solutions_Architect/
├── compliance-mapping/         # Framework alignment matrix
├── customer-case-studies/      # Fintech, healthcare, e-commerce scenarios
├── executive-summaries/        # Architecture overview, cost analysis, scalability roadmap
├── implementation-timelines/   # Phased rollout planning
├── playbooks/                  # Incident response procedures
└── docs/
    ├── architecture/           # ADRs and technical decisions
    ├── well-architected/       # AWS Well-Architected analysis
    ├── compliance/             # Regulatory alignment
    ├── cost-analysis/          # TCO breakdown
    ├── disaster-recovery/      # Business continuity
    └── migration/              # Migration planning
```

## Key Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Auth | Cognito + Lambda Authorizer | Managed auth with custom tenant isolation logic |
| API Layer | API Gateway (no ALB) | Cost savings, managed TLS, built-in throttling |
| Compute | ECS on EC2 (t3.micro) | 50% cheaper than Fargate for persistent workloads |
| Primary DB | Aurora Serverless v2 | Auto-scaling 0.5-1 ACU, pay-per-use |
| NoSQL | DynamoDB + DAX | Tenant-partitioned, microsecond reads |
| WAF | Managed rules + custom CVE rule | Core protection without Shield Advanced cost |
| Audit | CloudTrail + Config | API logging + resource compliance at minimal cost |
| IaC | Terraform (modular) | 13 modules, reproducible, auditable |

## Application Services

- Subscription Service — Cognito integration, plan management, billing, transaction logging
- Support Service — Ticket CRUD with tenant isolation, priority-based routing
- Frontend Service — Responsive web UI with OAuth callback handling
- Notification Router — Lambda-based intelligent ticket routing to team-specific SNS topics

## Deployment

```bash
# Automated
./deploy.sh

# Manual
terraform init
terraform plan
terraform apply
```

Requires: AWS CLI configured, Terraform >= 1.0

## Project Structure

```
├── main.tf / variables.tf / outputs.tf
├── modules/
│   ├── networking/          # VPC, subnets, security groups
│   ├── compute/             # ECS cluster and services
│   ├── database/            # Aurora Serverless v2, DynamoDB
│   ├── auth/                # Cognito + Lambda authorizer
│   ├── api/                 # API Gateway with VPC Links
│   ├── cache/               # ElastiCache Valkey
│   ├── security/            # IAM roles and policies
│   ├── security-compliance/ # WAF, CloudTrail, AWS Config
│   ├── monitoring/          # CloudWatch dashboards and alarms
│   ├── notifications/       # SNS + Lambda ticket router
│   ├── storage/             # S3 buckets
│   ├── ecr/                 # Container registry
│   └── cicd/                # CodeBuild + CodePipeline
├── apps/                    # Service application code
│   ├── auth-service/
│   ├── balance-service/
│   ├── support-service/
│   └── frontend/
├── docker/                  # Multi-stage Dockerfiles
├── migrations/              # Database schema management
└── Solutions_Architect/     # SA portfolio materials
```

## What This Demonstrates

- Implementing multi-tenant security with Cognito RBAC and tenant-scoped data isolation
- Writing CVE-specific WAF rules alongside managed rule sets
- Building audit infrastructure (CloudTrail + Config) into the platform from day one
- Documenting architecture decisions with explicit tradeoffs (cost vs security vs complexity)
- Producing SA-ready materials (case studies, compliance mapping, incident response playbooks)
