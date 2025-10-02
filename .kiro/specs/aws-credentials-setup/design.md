# Design Document

## Overview

This design document outlines multiple approaches for configuring AWS credentials to resolve the "No valid credential sources found" error when running Terraform. The solution provides flexibility for different environments while maintaining security best practices and ease of use.

## Architecture

### Credential Provider Chain

AWS SDK and Terraform follow a specific order when looking for credentials:

```
1. Environment Variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
2. Shared Credentials File (~/.aws/credentials)
3. Shared Config File (~/.aws/config)
4. IAM Roles for EC2 Instances
5. IAM Roles for ECS Tasks
6. IAM Roles for Lambda Functions
```

### Recommended Approaches by Environment

**Local Development**: AWS CLI configuration with profiles
**CI/CD Pipelines**: Environment variables with temporary credentials
**Production**: IAM roles with cross-account access
**Testing**: Environment variables or AWS CLI profiles

## Components and Interfaces

### Method 1: AWS CLI Configuration (Recommended for Local Development)

**Installation and Setup**:
```bash
# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure credentials
aws configure
```

**Configuration Files**:
- `~/.aws/credentials`: Stores access keys
- `~/.aws/config`: Stores region and output preferences

**Profile Management**:
```bash
# Configure default profile
aws configure

# Configure named profile
aws configure --profile saas-dev

# Use specific profile with Terraform
export AWS_PROFILE=saas-dev
terraform plan
```

### Method 2: Environment Variables (Recommended for CI/CD)

**Basic Environment Variables**:
```bash
export AWS_ACCESS_KEY_ID="your-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-access-key"
export AWS_DEFAULT_REGION="eu-west-2"
```

**With Session Token (for temporary credentials)**:
```bash
export AWS_ACCESS_KEY_ID="your-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-access-key"
export AWS_SESSION_TOKEN="your-session-token"
export AWS_DEFAULT_REGION="eu-west-2"
```

**Profile-specific Environment Variable**:
```bash
export AWS_PROFILE="saas-dev"
```

### Method 3: IAM Roles (Recommended for Production)

**Cross-Account Role Configuration**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::TRUSTED-ACCOUNT:user/terraform-user"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "unique-external-id"
        }
      }
    }
  ]
}
```

**Terraform Provider Configuration**:
```hcl
provider "aws" {
  region = var.region
  
  assume_role {
    role_arn     = "arn:aws:iam::TARGET-ACCOUNT:role/TerraformRole"
    session_name = "terraform-session"
    external_id  = "unique-external-id"
  }
}
```

## Data Models

### Required IAM Permissions

**Minimum Policy for SaaS Platform Infrastructure**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:*",
        "ecs:*",
        "rds:*",
        "elasticache:*",
        "s3:*",
        "lambda:*",
        "apigateway:*",
        "cognito-idp:*",
        "dynamodb:*",
        "dax:*",
        "iam:*",
        "logs:*",
        "sns:*",
        "cloudwatch:*",
        "application-autoscaling:*",
        "elasticloadbalancing:*"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sts:AssumeRole",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

### Credential Validation Commands

**Test AWS Connectivity**:
```bash
# Check current identity
aws sts get-caller-identity

# Test specific service access
aws ec2 describe-regions
aws s3 ls
aws iam list-users
```

**Terraform-specific Validation**:
```bash
# Initialize Terraform
terraform init

# Validate configuration
terraform validate

# Plan without applying
terraform plan
```

## Error Handling

### Common Error Scenarios

**"No valid credential sources found"**:
- **Cause**: No credentials configured
- **Solution**: Configure using one of the methods above
- **Validation**: Run `aws sts get-caller-identity`

**"Access Denied" errors**:
- **Cause**: Insufficient IAM permissions
- **Solution**: Update IAM policy with required permissions
- **Validation**: Test specific service access

**"Invalid security token"**:
- **Cause**: Expired temporary credentials
- **Solution**: Refresh credentials or use long-term keys
- **Validation**: Check token expiration time

**"Region not specified"**:
- **Cause**: Missing region configuration
- **Solution**: Set AWS_DEFAULT_REGION or configure in profile
- **Validation**: Run `aws configure list`

### Troubleshooting Steps

1. **Verify Credential Configuration**:
   ```bash
   aws configure list
   aws sts get-caller-identity
   ```

2. **Check Environment Variables**:
   ```bash
   env | grep AWS
   ```

3. **Test Service Access**:
   ```bash
   aws ec2 describe-regions --region eu-west-2
   ```

4. **Validate Terraform Configuration**:
   ```bash
   terraform init
   terraform validate
   ```

## Testing Strategy

### Credential Validation Script

```bash
#!/bin/bash
# validate_aws_credentials.sh

echo "=== AWS Credential Validation ==="

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not installed"
    exit 1
fi

# Check current identity
echo "🔍 Checking AWS identity..."
if aws sts get-caller-identity; then
    echo "✅ AWS credentials are valid"
else
    echo "❌ AWS credentials are invalid or not configured"
    exit 1
fi

# Check region configuration
echo "🌍 Checking region configuration..."
REGION=$(aws configure get region)
if [ -z "$REGION" ]; then
    echo "⚠️  No default region configured"
    echo "💡 Set region with: aws configure set region eu-west-2"
else
    echo "✅ Default region: $REGION"
fi

# Test service access
echo "🧪 Testing service access..."
services=("ec2" "s3" "iam" "rds" "lambda")
for service in "${services[@]}"; do
    case $service in
        "ec2")
            if aws ec2 describe-regions --region ${REGION:-eu-west-2} &>/dev/null; then
                echo "✅ EC2 access: OK"
            else
                echo "❌ EC2 access: FAILED"
            fi
            ;;
        "s3")
            if aws s3 ls &>/dev/null; then
                echo "✅ S3 access: OK"
            else
                echo "❌ S3 access: FAILED"
            fi
            ;;
        "iam")
            if aws iam get-user &>/dev/null; then
                echo "✅ IAM access: OK"
            else
                echo "❌ IAM access: FAILED"
            fi
            ;;
        "rds")
            if aws rds describe-db-instances --region ${REGION:-eu-west-2} &>/dev/null; then
                echo "✅ RDS access: OK"
            else
                echo "❌ RDS access: FAILED"
            fi
            ;;
        "lambda")
            if aws lambda list-functions --region ${REGION:-eu-west-2} &>/dev/null; then
                echo "✅ Lambda access: OK"
            else
                echo "❌ Lambda access: FAILED"
            fi
            ;;
    esac
done

echo "=== Validation Complete ==="
```

### Terraform Validation

```bash
#!/bin/bash
# validate_terraform_aws.sh

echo "=== Terraform AWS Validation ==="

# Initialize Terraform
echo "🔧 Initializing Terraform..."
if terraform init; then
    echo "✅ Terraform initialization successful"
else
    echo "❌ Terraform initialization failed"
    exit 1
fi

# Validate configuration
echo "🔍 Validating Terraform configuration..."
if terraform validate; then
    echo "✅ Terraform configuration is valid"
else
    echo "❌ Terraform configuration is invalid"
    exit 1
fi

# Plan (dry run)
echo "📋 Running Terraform plan..."
if terraform plan -out=tfplan; then
    echo "✅ Terraform plan successful"
    echo "💡 Run 'terraform apply tfplan' to apply changes"
else
    echo "❌ Terraform plan failed"
    echo "💡 Check AWS credentials and permissions"
    exit 1
fi

echo "=== Terraform Validation Complete ==="
```

## Security Considerations

### Best Practices

1. **Never commit credentials to version control**:
   - Add `.aws/` to `.gitignore`
   - Use environment variables in CI/CD
   - Scan repositories for accidentally committed keys

2. **Use least privilege principle**:
   - Create specific IAM policies for Terraform
   - Avoid using root account credentials
   - Regular permission audits

3. **Rotate credentials regularly**:
   - Set up automatic key rotation
   - Monitor key age in AWS console
   - Use temporary credentials when possible

4. **Monitor credential usage**:
   - Enable CloudTrail logging
   - Set up alerts for unusual activity
   - Regular access reviews

### Environment-Specific Security

**Development**:
- Use personal AWS accounts or sandbox environments
- Implement spending limits and resource quotas
- Regular cleanup of unused resources

**Production**:
- Use IAM roles instead of access keys
- Implement MFA requirements
- Cross-account role assumptions
- Comprehensive logging and monitoring

## Implementation Notes

### Quick Start Guide

1. **Install AWS CLI**:
   ```bash
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip
   sudo ./aws/install
   ```

2. **Configure Credentials**:
   ```bash
   aws configure
   # Enter: Access Key ID, Secret Access Key, Region (eu-west-2), Output format (json)
   ```

3. **Validate Setup**:
   ```bash
   aws sts get-caller-identity
   ```

4. **Create terraform.tfvars**:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your specific values
   ```

5. **Run Terraform**:
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

### Alternative: Environment Variables Only

If you prefer not to use AWS CLI configuration:

```bash
export AWS_ACCESS_KEY_ID="your-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-access-key"
export AWS_DEFAULT_REGION="eu-west-2"

terraform init
terraform plan
```

### CI/CD Integration

For GitHub Actions, GitLab CI, or other CI/CD systems:

```yaml
# Example GitHub Actions
env:
  AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
  AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
  AWS_DEFAULT_REGION: eu-west-2
```

Store credentials as encrypted secrets in your CI/CD platform, never in plain text configuration files.