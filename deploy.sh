#!/bin/bash

echo "🚀 Deploying SaaS Platform..."

# Check if terraform.tfvars exists
if [ ! -f "terraform.tfvars" ]; then
    echo "📝 Creating terraform.tfvars from example..."
    cp terraform.tfvars.example terraform.tfvars
    echo "✅ Please review terraform.tfvars and update any values as needed"
fi

# Initialize Terraform
echo "🔧 Initializing Terraform..."
terraform init

# Plan deployment
echo "📋 Planning deployment..."
terraform plan

# Ask for confirmation
read -p "🤔 Do you want to proceed with deployment? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 Applying Terraform configuration..."
    terraform apply -auto-approve
    
    echo ""
    echo "🎉 Deployment complete!"
    echo ""
    echo "📊 Outputs:"
    terraform output
    
    echo ""
    echo "🌐 Access your SaaS platform at:"
    echo "ALB DNS: $(terraform output -raw alb_dns_name)"
    echo "API Gateway: $(terraform output -raw api_gateway_url)"
    echo ""
    echo "👤 Demo accounts:"
    echo "- demo@democorp.com / demo123"
    echo "- demo@testinc.com / demo123"
    echo "- demo@enterpriseltd.com / demo123"
    
else
    echo "❌ Deployment cancelled"
fi