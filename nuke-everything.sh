#!/bin/bash

# Nuclear Option - Complete Infrastructure Destruction
# Use with extreme caution!

set -e

PROJECT_NAME="saas-platform"
REGION="eu-west-2"

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${RED}☢️  NUCLEAR OPTION - COMPLETE DESTRUCTION${NC}"
echo -e "${RED}=========================================${NC}"
echo ""
echo -e "${YELLOW}⚠️  WARNING: This will destroy ALL infrastructure!${NC}"
echo -e "${YELLOW}⚠️  This action is IRREVERSIBLE!${NC}"
echo ""
echo "This will:"
echo "• Clean all ECR repositories"
echo "• Destroy all Terraform resources"
echo "• Remove all AWS resources for project: $PROJECT_NAME"
echo ""

read -p "Are you absolutely sure? Type 'NUKE' to confirm: " confirmation

if [ "$confirmation" != "NUKE" ]; then
    echo "❌ Aborted. Infrastructure preserved."
    exit 1
fi

echo ""
echo -e "${RED}🚀 Beginning nuclear destruction...${NC}"

# Step 1: Clean ECR repositories first
echo "Step 1: Cleaning ECR repositories..."
./cleanup-helper.sh ecr || echo "ECR cleanup failed, continuing..."

# Step 2: Attempt graceful Terraform destroy
echo "Step 2: Attempting Terraform destroy..."
terraform destroy -auto-approve || echo "Terraform destroy had errors, continuing with force cleanup..."

# Step 3: Force cleanup remaining resources
echo "Step 3: Force cleanup of stubborn resources..."

# Force delete ECR repositories
echo "Force deleting ECR repositories..."
for repo in "frontend" "subscription-service" "support-service"; do
    aws ecr delete-repository \
        --repository-name "${PROJECT_NAME}/${repo}" \
        --region $REGION \
        --force 2>/dev/null || echo "Repository ${repo} already deleted or not found"
done

# Force delete RDS instances (skip final snapshot)
echo "Force deleting RDS instances..."
aws rds describe-db-instances \
    --region $REGION \
    --query "DBInstances[?starts_with(DBInstanceIdentifier, '${PROJECT_NAME}')].DBInstanceIdentifier" \
    --output text | while read instance; do
    if [ ! -z "$instance" ]; then
        echo "Deleting RDS instance: $instance"
        aws rds delete-db-instance \
            --db-instance-identifier "$instance" \
            --region $REGION \
            --skip-final-snapshot 2>/dev/null || echo "Failed to delete $instance"
    fi
done

# Force delete RDS cluster
echo "Force deleting RDS cluster..."
aws rds delete-db-cluster \
    --db-cluster-identifier "${PROJECT_NAME}-cluster" \
    --region $REGION \
    --skip-final-snapshot 2>/dev/null || echo "RDS cluster already deleted or not found"

# Clean up ECS services and cluster
echo "Cleaning ECS services..."
aws ecs list-services \
    --cluster "${PROJECT_NAME}-cluster" \
    --region $REGION \
    --query "serviceArns" \
    --output text 2>/dev/null | while read service; do
    if [ ! -z "$service" ]; then
        echo "Deleting ECS service: $service"
        aws ecs delete-service \
            --cluster "${PROJECT_NAME}-cluster" \
            --service "$service" \
            --region $REGION \
            --force 2>/dev/null || echo "Failed to delete service $service"
    fi
done

aws ecs delete-cluster \
    --cluster "${PROJECT_NAME}-cluster" \
    --region $REGION 2>/dev/null || echo "ECS cluster already deleted or not found"

# Clean up S3 buckets (force delete with contents)
echo "Force deleting S3 buckets..."
aws s3 ls | grep "$PROJECT_NAME" | awk '{print $3}' | while read bucket; do
    if [ ! -z "$bucket" ]; then
        echo "Deleting S3 bucket: $bucket"
        aws s3 rm "s3://$bucket" --recursive 2>/dev/null || echo "Failed to empty $bucket"
        aws s3 rb "s3://$bucket" --force 2>/dev/null || echo "Failed to delete $bucket"
    fi
done

# Note about Macie jobs
echo ""
echo -e "${YELLOW}ℹ️  Note: Macie classification jobs cannot be deleted once completed.${NC}"
echo -e "${YELLOW}   They will remain in your account but won't incur ongoing costs.${NC}"

echo ""
echo -e "${GREEN}☢️  Nuclear destruction complete!${NC}"
echo -e "${GREEN}✅ All infrastructure has been destroyed.${NC}"
echo ""
echo "Remaining items (cannot be deleted):"
echo "• Macie classification jobs (completed jobs are permanent)"
echo "• CloudTrail logs (if any)"
echo "• Any manually created resources outside Terraform"