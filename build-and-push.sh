#!/bin/bash

# Build and Push Docker Images to ECR
# Usage: ./build-and-push.sh [tag]

set -e

# Configuration
PROJECT_NAME="saas-platform"
REGION="eu-west-2"
TAG=${1:-latest}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
print_status "Checking prerequisites..."

if ! command_exists aws; then
    print_error "AWS CLI is not installed. Please install it first."
    exit 1
fi

if ! command_exists docker; then
    print_error "Docker is not installed. Please install it first."
    exit 1
fi

# Get AWS account ID
print_status "Getting AWS account ID..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
if [ $? -ne 0 ]; then
    print_error "Failed to get AWS account ID. Please check your AWS credentials."
    exit 1
fi
print_success "AWS Account ID: $ACCOUNT_ID"

# ECR repository URLs
ECR_BASE="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"
FRONTEND_REPO="$ECR_BASE/$PROJECT_NAME/frontend"
SUBSCRIPTION_REPO="$ECR_BASE/$PROJECT_NAME/subscription-service"
SUPPORT_REPO="$ECR_BASE/$PROJECT_NAME/support-service"

# Login to ECR
print_status "Logging in to ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_BASE
if [ $? -ne 0 ]; then
    print_error "Failed to login to ECR"
    exit 1
fi
print_success "Successfully logged in to ECR"

# Function to build and push image
build_and_push() {
    local service_name=$1
    local dockerfile_path=$2
    local repo_url=$3
    local build_context=$4
    
    print_status "Building $service_name image..."
    
    # Build the image with correct context
    docker build -t $service_name:$TAG -f $dockerfile_path $build_context
    if [ $? -ne 0 ]; then
        print_error "Failed to build $service_name image"
        return 1
    fi
    
    # Tag for ECR
    docker tag $service_name:$TAG $repo_url:$TAG
    docker tag $service_name:$TAG $repo_url:latest
    
    print_status "Pushing $service_name image to ECR..."
    
    # Push to ECR
    docker push $repo_url:$TAG
    docker push $repo_url:latest
    
    if [ $? -ne 0 ]; then
        print_error "Failed to push $service_name image"
        return 1
    fi
    
    print_success "Successfully pushed $service_name:$TAG to ECR"
    
    # Clean up local images to save space
    docker rmi $service_name:$TAG $repo_url:$TAG $repo_url:latest 2>/dev/null || true
}

# Build and push frontend
print_status "=== Building Frontend Service ==="
build_and_push "frontend" "docker/frontend/Dockerfile" $FRONTEND_REPO "docker/frontend"

# Build and push subscription service
print_status "=== Building Subscription Service ==="
build_and_push "subscription-service" "docker/subscription-service/Dockerfile" $SUBSCRIPTION_REPO "."

# Build and push support service
print_status "=== Building Support Service ==="
build_and_push "support-service" "docker/support-service/Dockerfile" $SUPPORT_REPO "."

print_success "=== All images built and pushed successfully! ==="

# Display image information
print_status "=== Image Information ==="
echo "Frontend:        $FRONTEND_REPO:$TAG"
echo "Subscription:    $SUBSCRIPTION_REPO:$TAG"
echo "Support:         $SUPPORT_REPO:$TAG"

print_status "=== Next Steps ==="
echo "1. Update your ECS task definitions to use these image URLs"
echo "2. Deploy your ECS services with: terraform apply"
echo "3. Check ECS service status in AWS Console"

# Optional: Update ECS services if they exist
print_warning "To update running ECS services, run:"
echo "aws ecs update-service --cluster $PROJECT_NAME-cluster --service $PROJECT_NAME-frontend --force-new-deployment --region $REGION"
echo "aws ecs update-service --cluster $PROJECT_NAME-cluster --service $PROJECT_NAME-subscription-service --force-new-deployment --region $REGION"
echo "aws ecs update-service --cluster $PROJECT_NAME-cluster --service $PROJECT_NAME-support-service --force-new-deployment --region $REGION"