#!/usr/bin/env python3
"""
Test script for the intelligent SNS notification system
Creates test tickets with different priorities and content to verify routing
"""

import boto3
import json
import uuid
from datetime import datetime

def test_notification_routing():
    """Test the intelligent ticket routing system"""
    
    # AWS clients
    sns = boto3.client('sns', region_name='eu-west-2')
    
    # Get the main SNS topic ARN (you'll need to update this)
    try:
        ssm = boto3.client('ssm', region_name='eu-west-2')
        topic_arn = ssm.get_parameter(Name='/saas-platform/notifications/sns_topic_arn')['Parameter']['Value']
    except Exception as e:
        print(f"❌ Could not get SNS topic ARN: {e}")
        print("Please ensure the infrastructure is deployed and try again.")
        return
    
    # Test cases for different routing scenarios
    test_tickets = [
        {
            "ticket_id": str(uuid.uuid4()),
            "subject": "URGENT: System Down",
            "description": "The entire system is not responding and customers cannot access their accounts",
            "priority": "urgent",
            "tenant_id": "test-tenant-1",
            "created_by": "test-user",
            "created_at": datetime.utcnow().isoformat(),
            "expected_route": "urgent"
        },
        {
            "ticket_id": str(uuid.uuid4()),
            "subject": "Password Reset Not Working",
            "description": "Users are unable to reset their passwords. The reset email is not being sent.",
            "priority": "high",
            "tenant_id": "test-tenant-2",
            "created_by": "test-user",
            "created_at": datetime.utcnow().isoformat(),
            "expected_route": "password_reset"
        },
        {
            "ticket_id": str(uuid.uuid4()),
            "subject": "Billing Question",
            "description": "Customer was charged twice for their subscription this month. Need to process refund.",
            "priority": "medium",
            "tenant_id": "test-tenant-3",
            "created_by": "test-user",
            "created_at": datetime.utcnow().isoformat(),
            "expected_route": "billing"
        },
        {
            "ticket_id": str(uuid.uuid4()),
            "subject": "API Error 500",
            "description": "The API is returning 500 errors for database connections. Server logs show timeout issues.",
            "priority": "high",
            "tenant_id": "test-tenant-4",
            "created_by": "test-user",
            "created_at": datetime.utcnow().isoformat(),
            "expected_route": "technical"
        },
        {
            "ticket_id": str(uuid.uuid4()),
            "subject": "Feature Request",
            "description": "Would like to see more detailed analytics in the dashboard with export functionality.",
            "priority": "low",
            "tenant_id": "test-tenant-5",
            "created_by": "test-user",
            "created_at": datetime.utcnow().isoformat(),
            "expected_route": "general"
        }
    ]
    
    print("🧪 Testing Intelligent SNS Notification Routing")
    print("=" * 60)
    print(f"SNS Topic ARN: {topic_arn}")
    print()
    
    for i, ticket in enumerate(test_tickets, 1):
        print(f"📧 Test {i}: {ticket['subject']}")
        print(f"   Priority: {ticket['priority']}")
        print(f"   Expected Route: {ticket['expected_route']}")
        
        try:
            # Publish to main SNS topic
            response = sns.publish(
                TopicArn=topic_arn,
                Subject=f"Test Ticket: {ticket['subject']}",
                Message=json.dumps(ticket, indent=2),
                MessageAttributes={
                    'priority': {
                        'DataType': 'String',
                        'StringValue': ticket['priority']
                    },
                    'ticket_id': {
                        'DataType': 'String',
                        'StringValue': ticket['ticket_id']
                    },
                    'test': {
                        'DataType': 'String',
                        'StringValue': 'true'
                    }
                }
            )
            
            print(f"   ✅ Published successfully (MessageId: {response['MessageId']})")
            
        except Exception as e:
            print(f"   ❌ Failed to publish: {e}")
        
        print()
    
    print("🎯 Test Results:")
    print("Check your email inboxes for the following expected notifications:")
    print("• bilalkwj@amazon.com - Should receive URGENT ticket")
    print("• support-password@example.com - Should receive password reset ticket")
    print("• billing-support@example.com - Should receive billing question")
    print("• tech-support@example.com - Should receive API error ticket")
    print("• general-support@example.com - Should receive feature request")
    print()
    print("📋 Note: You may need to confirm SNS email subscriptions first!")
    print("Check AWS SNS Console for subscription confirmations.")

def check_sns_subscriptions():
    """Check the status of SNS topic subscriptions"""
    try:
        sns = boto3.client('sns', region_name='eu-west-2')
        
        # List all topics
        topics = sns.list_topics()
        
        print("📊 SNS Topic Subscription Status")
        print("=" * 50)
        
        for topic in topics['Topics']:
            topic_arn = topic['TopicArn']
            if 'saas-platform' in topic_arn:
                topic_name = topic_arn.split(':')[-1]
                print(f"\n🔔 {topic_name}")
                
                # Get subscriptions for this topic
                subscriptions = sns.list_subscriptions_by_topic(TopicArn=topic_arn)
                
                if subscriptions['Subscriptions']:
                    for sub in subscriptions['Subscriptions']:
                        status = sub.get('SubscriptionArn', 'PendingConfirmation')
                        endpoint = sub['Endpoint']
                        protocol = sub['Protocol']
                        
                        if status == 'PendingConfirmation':
                            print(f"   ⏳ {protocol}:{endpoint} - Pending Confirmation")
                        else:
                            print(f"   ✅ {protocol}:{endpoint} - Confirmed")
                else:
                    print("   📭 No subscriptions")
        
        print("\n💡 To confirm email subscriptions:")
        print("1. Check your email inboxes for AWS SNS confirmation emails")
        print("2. Click the 'Confirm subscription' link in each email")
        print("3. Re-run this script to verify confirmations")
        
    except Exception as e:
        print(f"❌ Error checking subscriptions: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--check-subscriptions":
        check_sns_subscriptions()
    else:
        test_notification_routing()
        print("\n" + "="*60)
        print("💡 To check subscription status, run:")
        print("   python3 test_notifications.py --check-subscriptions")