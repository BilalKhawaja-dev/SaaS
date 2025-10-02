#!/bin/bash

echo "🚀 Deploying Multi-AZ SaaS Platform..."

# Check if terraform.tfvars exists
if [ ! -f "terraform.tfvars" ]; then
    echo "📝 Creating terraform.tfvars from example..."
    cp terraform.tfvars.example terraform.tfvars
    echo "✅ Please review terraform.tfvars and update any values as needed"
fi

# Build Lambda packages
echo "📦 Building Lambda packages..."
if [ -f "modules/api/build_authorizer.sh" ]; then
    ./modules/api/build_authorizer.sh
fi

if [ -f "modules/auth/build_token_customizer.sh" ]; then
    ./modules/auth/build_token_customizer.sh
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
    echo "🗄️ Running database migrations..."
    if command -v python3 &> /dev/null; then
        cd migrations
        python3 run_migrations.py
        cd ..
        echo "✅ Database migrations completed"
    else
        echo "⚠️ Python3 not found. Please run database migrations manually:"
        echo "   cd migrations && python3 run_migrations.py"
    fi
    
    echo ""
    echo "🎉 Deployment complete!"
    echo ""
    echo "📊 Infrastructure Outputs:"
    terraform output
    
    echo ""
    echo "🌐 Access your SaaS platform:"
    echo "API Gateway URL: $(terraform output -raw api_gateway_url)"
    echo "Cognito Hosted UI: $(terraform output -raw cognito_hosted_ui_url)"
    
    echo ""
    echo "👤 Demo accounts (use Cognito Hosted UI):"
    echo "- admin@democorp.com / Admin123! (Admin access)"
    echo "- user@testinc.com / User123! (Read-only access)"
    echo "- readonly@enterpriseltd.com / Readonly123! (Read-only access)"
    
    echo ""
    echo "📈 Monitoring:"
    echo "- CloudWatch Dashboard: AWS Console → CloudWatch → Dashboards"
    echo "- Logs: AWS Console → CloudWatch → Log Groups"
    echo "- Alarms: AWS Console → CloudWatch → Alarms"
    
    echo ""
    echo "📧 SNS Notification System:"
    echo "✅ Intelligent ticket routing deployed"
    echo "- Urgent tickets → bilalkwj@amazon.com"
    echo "- Password issues → support-password@example.com"
    echo "- Billing questions → billing-support@example.com"
    echo "- Technical issues → tech-support@example.com"
    echo "- General support → general-support@example.com"
    echo ""
    echo "🧪 Test the notification system:"
    echo "python3 test_notifications.py"
    
    echo ""
    echo "🔧 Architecture Features:"
    echo "✅ Multi-AZ deployment (eu-west-2a, eu-west-2b)"
    echo "✅ API Gateway-first (no ALB)"
    echo "✅ Aurora Serverless v2 with RDS Proxy"
    echo "✅ Valkey replication group with failover"
    echo "✅ DAX cluster for DynamoDB acceleration"
    echo "✅ Lambda authorizer with Cognito JWKS validation"
    echo "✅ Intelligent SNS notification routing"
    echo "✅ Comprehensive monitoring and alerting"
    
else
    echo "❌ Deployment cancelled"
fi