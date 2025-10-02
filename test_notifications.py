#!/usr/bin/env python3
"""
Test script for SNS notification system
Tests the intelligent routing of support tickets to different teams
"""

import requests
import json
import time
import sys
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:8080"  # API Gateway URL
TEST_TICKETS = [
    {
        "subject": "URGENT: System Down",
        "description": "The entire system is not responding. All users are affected.",
        "priority": "urgent"
    },
    {
        "subject": "Password Reset Issue",
        "description": "I forgot my password and the reset email is not working",
        "priority": "high"
    },
    {
        "subject": "Billing Question",
        "description": "I was charged twice for my subscription this month",
        "priority": "medium"
    },
    {
        "subject": "API Integration Problem",
        "description": "Getting 500 errors when calling the user management API",
        "priority": "high"
    },
    {
        "subject": "General Question",
        "description": "How do I export my data from the platform?",
        "priority": "low"
    },
    {
        "subject": "Login Authentication Error",
        "description": "Cannot authenticate with my credentials, getting invalid token error",
        "priority": "medium"
    },
    {
        "subject": "Payment Method Update",
        "description": "Need to update my credit card information for billing",
        "priority": "low"
    },
    {
        "subject": "Database Connection Timeout",
        "description": "Application is showing database connection timeouts frequently",
        "priority": "high"
    }
]

def get_auth_token():
    """
    Get authentication token for testing
    In a real scenario, this would use Cognito authentication
    """
    # For testing, we'll use a mock token
    # In production, implement proper Cognito authentication
    return "mock-jwt-token-for-testing"

def create_test_ticket(ticket_data, auth_token):
    """Create a test support ticket"""
    headers = {
        'Authorization': f'Bearer {auth_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/support/tickets",
            headers=headers,
            json=ticket_data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Created ticket: {result.get('ticket_id')} - {ticket_data['subject']}")
            if ticket_data['priority'] == 'urgent':
                print(f"   🚨 Urgent notification: {result.get('urgent_notification_sent', 'Unknown')}")
            return result.get('ticket_id')
        else:
            print(f"❌ Failed to create ticket: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error creating ticket: {e}")
        return None

def test_ticket_routing():
    """Test the intelligent ticket routing system"""
    print("🧪 Testing SNS Notification System")
    print("=" * 50)
    
    auth_token = get_auth_token()
    created_tickets = []
    
    for i, ticket_data in enumerate(TEST_TICKETS, 1):
        print(f"\n📝 Test {i}/{len(TEST_TICKETS)}: {ticket_data['subject']}")
        print(f"   Priority: {ticket_data['priority']}")
        print(f"   Expected routing: {predict_routing(ticket_data)}")
        
        ticket_id = create_test_ticket(ticket_data, auth_token)
        if ticket_id:
            created_tickets.append(ticket_id)
        
        # Small delay between requests
        time.sleep(1)
    
    print(f"\n📊 Summary: Created {len(created_tickets)} test tickets")
    print("\n🔍 Expected Routing Results:")
    print("- Urgent tickets → bilalkwj@amazon.com")
    print("- Password/Auth tickets → support-password@example.com")
    print("- Billing tickets → billing-support@example.com")
    print("- Technical tickets → tech-support@example.com")
    print("- General tickets → general-support@example.com")
    
    return created_tickets

def predict_routing(ticket_data):
    """Predict which team should receive the ticket"""
    if ticket_data['priority'] == 'urgent':
        return "Urgent Team (bilalkwj@amazon.com)"
    
    content = f"{ticket_data['subject']} {ticket_data['description']}".lower()
    
    if any(keyword in content for keyword in ['password', 'login', 'auth', 'authentication']):
        return "Password Reset Team"
    elif any(keyword in content for keyword in ['billing', 'payment', 'charge', 'subscription']):
        return "Billing Team"
    elif any(keyword in content for keyword in ['api', 'database', 'connection', 'timeout', 'error']):
        return "Technical Team"
    else:
        return "General Support Team"

def test_sns_topics():
    """Test SNS topic configuration"""
    print("\n🔧 Testing SNS Topic Configuration")
    print("=" * 40)
    
    try:
        import boto3
        sns = boto3.client('sns', region_name='eu-west-2')
        
        # List topics to verify they exist
        topics = sns.list_topics()
        saas_topics = [topic for topic in topics['Topics'] 
                      if 'saas-platform' in topic['TopicArn']]
        
        print(f"✅ Found {len(saas_topics)} SaaS platform SNS topics:")
        for topic in saas_topics:
            topic_name = topic['TopicArn'].split(':')[-1]
            print(f"   - {topic_name}")
            
            # Check subscriptions
            subs = sns.list_subscriptions_by_topic(TopicArn=topic['TopicArn'])
            print(f"     Subscriptions: {len(subs['Subscriptions'])}")
            
    except Exception as e:
        print(f"❌ Error checking SNS topics: {e}")
        print("   Make sure AWS credentials are configured and topics are deployed")

def test_lambda_function():
    """Test Lambda function configuration"""
    print("\n⚡ Testing Lambda Function Configuration")
    print("=" * 45)
    
    try:
        import boto3
        lambda_client = boto3.client('lambda', region_name='eu-west-2')
        
        function_name = 'saas-platform-ticket-router'
        
        # Get function configuration
        response = lambda_client.get_function(FunctionName=function_name)
        
        print(f"✅ Lambda function '{function_name}' found")
        print(f"   Runtime: {response['Configuration']['Runtime']}")
        print(f"   Timeout: {response['Configuration']['Timeout']}s")
        
        # Check environment variables
        env_vars = response['Configuration'].get('Environment', {}).get('Variables', {})
        expected_vars = [
            'URGENT_TOPIC_ARN',
            'PASSWORD_RESET_TOPIC_ARN', 
            'BILLING_TOPIC_ARN',
            'TECHNICAL_TOPIC_ARN',
            'GENERAL_TOPIC_ARN'
        ]
        
        for var in expected_vars:
            if var in env_vars:
                print(f"   ✅ {var}: configured")
            else:
                print(f"   ❌ {var}: missing")
                
    except Exception as e:
        print(f"❌ Error checking Lambda function: {e}")
        print("   Make sure the Lambda function is deployed")

def main():
    """Main test function"""
    print("🚀 SaaS Platform SNS Notification System Test")
    print("=" * 60)
    print(f"Test started at: {datetime.now().isoformat()}")
    
    # Test infrastructure
    test_sns_topics()
    test_lambda_function()
    
    # Test ticket creation and routing
    created_tickets = test_ticket_routing()
    
    print("\n" + "=" * 60)
    print("📧 Check your email inboxes for notifications:")
    print("- bilalkwj@amazon.com (urgent tickets)")
    print("- support-password@example.com (password issues)")
    print("- billing-support@example.com (billing questions)")
    print("- tech-support@example.com (technical issues)")
    print("- general-support@example.com (general questions)")
    
    print(f"\n✅ Test completed at: {datetime.now().isoformat()}")
    print(f"📊 Total tickets created: {len(created_tickets)}")

if __name__ == "__main__":
    main()