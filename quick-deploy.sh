#!/bin/bash

# Quick Deploy with Timestamp
# This avoids AWS Secrets Manager deletion conflicts

set -e

# Generate timestamp for unique deployment
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

echo "🚀 Quick Deploy with ID: $TIMESTAMP"

# Deploy with unique deployment ID
terraform apply -auto-approve -var="deployment_id=$TIMESTAMP"

echo "✅ Deployment complete with ID: $TIMESTAMP"
echo "💡 To destroy: terraform destroy -auto-approve -var=\"deployment_id=$TIMESTAMP\""