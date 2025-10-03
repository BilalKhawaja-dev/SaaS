#!/bin/bash

# Cleanup Helper Script
# Handles common AWS resource cleanup issues

set -e

PROJECT_NAME="saas-platform"
REGION="eu-west-2"

echo "🧹 AWS Cleanup Helper"
echo "====================="

# Function to clean ECR repositories
cleanup_ecr() {
    echo "🗑️  Cleaning ECR repositories..."
    
    for repo in "frontend" "subscription-service" "support-service"; do
        echo "Cleaning ${PROJECT_NAME}/${repo}..."
        
        # List and delete all images
        aws ecr list-images \
            --repository-name "${PROJECT_NAME}/${repo}" \
            --region $REGION \
            --query 'imageIds[*]' \
            --output json > /tmp/images.json 2>/dev/null || echo "Repository ${repo} not found or empty"
        
        if [ -s /tmp/images.json ] && [ "$(cat /tmp/images.json)" != "[]" ]; then
            aws ecr batch-delete-image \
                --repository-name "${PROJECT_NAME}/${repo}" \
                --region $REGION \
                --image-ids file:///tmp/images.json || echo "Failed to delete images from ${repo}"
        fi
    done
    
    rm -f /tmp/images.json
    echo "✅ ECR cleanup complete"
}

# Function to handle RDS instances
cleanup_rds() {
    echo "🗑️  Checking RDS instances..."
    
    # List RDS instances
    aws rds describe-db-instances \
        --region $REGION \
        --query "DBInstances[?starts_with(DBInstanceIdentifier, '${PROJECT_NAME}')].{ID:DBInstanceIdentifier,Status:DBInstanceStatus}" \
        --output table || echo "No RDS instances found"
    
    echo "ℹ️  If RDS instances are stuck, wait for them to finish creating before destroying"
}

# Function to check Macie jobs
check_macie() {
    echo "🔍 Checking Macie classification jobs..."
    
    aws macie2 list-classification-jobs \
        --region $REGION \
        --query "items[?contains(name, '${PROJECT_NAME}')].{Name:name,Status:jobStatus}" \
        --output table 2>/dev/null || echo "No Macie jobs found or Macie not enabled"
    
    echo "ℹ️  Macie jobs cannot be deleted once completed - they're set to prevent_destroy"
}

# Main menu
case "${1:-menu}" in
    "ecr")
        cleanup_ecr
        ;;
    "rds")
        cleanup_rds
        ;;
    "macie")
        check_macie
        ;;
    "all")
        cleanup_ecr
        cleanup_rds
        check_macie
        ;;
    *)
        echo "Usage: $0 [ecr|rds|macie|all]"
        echo ""
        echo "Commands:"
        echo "  ecr    - Clean ECR repositories (delete all images)"
        echo "  rds    - Check RDS instance status"
        echo "  macie  - Check Macie classification jobs"
        echo "  all    - Run all cleanup checks"
        echo ""
        echo "Example: $0 ecr"
        ;;
esac