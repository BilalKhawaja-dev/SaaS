import json
import boto3
import os
import re
from typing import Dict, Any

# Initialize SNS client
sns = boto3.client('sns')

# Topic ARNs from environment variables
TOPIC_MAPPING = {
    'urgent': os.environ['URGENT_TOPIC_ARN'],
    'password_reset': os.environ['PASSWORD_RESET_TOPIC_ARN'],
    'billing': os.environ['BILLING_TOPIC_ARN'],
    'technical': os.environ['TECHNICAL_TOPIC_ARN'],
    'general': os.environ['GENERAL_TOPIC_ARN']
}

# Keywords for intelligent routing
ROUTING_KEYWORDS = {
    'password_reset': [
        'password', 'reset', 'login', 'authentication', 'auth', 'signin', 
        'sign in', 'access', 'locked out', 'forgot password', 'cant login',
        'cannot login', 'username', 'credentials'
    ],
    'billing': [
        'billing', 'payment', 'invoice', 'charge', 'subscription', 'plan',
        'upgrade', 'downgrade', 'refund', 'credit card', 'payment method',
        'billing cycle', 'cost', 'price', 'pricing', 'fee', 'transaction'
    ],
    'technical': [
        'bug', 'error', 'crash', 'performance', 'slow', 'api', 'integration',
        'database', 'server', 'timeout', 'connection', 'ssl', 'certificate',
        'deployment', 'configuration', 'setup', 'installation', 'technical'
    ]
}

def categorize_ticket(subject: str, description: str, priority: str) -> str:
    """
    Categorize ticket based on content analysis
    """
    # Always route urgent tickets to urgent topic
    if priority == 'urgent':
        return 'urgent'
    
    # Combine subject and description for analysis
    content = f"{subject} {description}".lower()
    
    # Check for keyword matches
    for category, keywords in ROUTING_KEYWORDS.items():
        for keyword in keywords:
            if keyword in content:
                return category
    
    # Default to general support
    return 'general'

def lambda_handler(event, context):
    """
    Lambda function to route support tickets to appropriate SNS topics
    """
    try:
        # Parse SNS message
        for record in event['Records']:
            sns_message = json.loads(record['Sns']['Message'])
            
            # Extract ticket information
            ticket_id = sns_message.get('ticket_id', 'Unknown')
            subject = sns_message.get('subject', '')
            description = sns_message.get('description', '')
            priority = sns_message.get('priority', 'medium')
            tenant_id = sns_message.get('tenant_id', 'Unknown')
            created_by = sns_message.get('created_by', 'Unknown')
            
            # Categorize the ticket
            category = categorize_ticket(subject, description, priority)
            
            # Get target topic ARN
            target_topic_arn = TOPIC_MAPPING.get(category, TOPIC_MAPPING['general'])
            
            # Create enhanced message for specific team
            enhanced_message = create_enhanced_message(
                sns_message, category, ticket_id, subject, description, 
                priority, tenant_id, created_by
            )
            
            # Publish to appropriate topic
            response = sns.publish(
                TopicArn=target_topic_arn,
                Subject=f"[{category.upper()}] {subject}",
                Message=json.dumps(enhanced_message, default='json'),
                MessageStructure='json'
            )
            
            print(f"Routed ticket {ticket_id} to {category} team. MessageId: {response['MessageId']}")
        
        return {
            'statusCode': 200,
            'body': json.dumps('Tickets routed successfully')
        }
        
    except Exception as e:
        print(f"Error routing ticket: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }

def create_enhanced_message(original_message: Dict[str, Any], category: str, 
                          ticket_id: str, subject: str, description: str,
                          priority: str, tenant_id: str, created_by: str) -> Dict[str, str]:
    """
    Create enhanced message with team-specific information
    """
    
    # Base message for all formats
    base_info = f"""
Ticket ID: {ticket_id}
Category: {category.upper()}
Priority: {priority.upper()}
Subject: {subject}
Created by: {created_by}
Tenant ID: {tenant_id}
Created at: {original_message.get('created_at', 'Unknown')}

Description:
{description}
"""
    
    # Team-specific instructions
    team_instructions = {
        'urgent': "🚨 URGENT TICKET - Immediate response required within 15 minutes!",
        'password_reset': "🔐 Password/Authentication Issue - Check user account status and reset procedures.",
        'billing': "💳 Billing/Payment Issue - Review account billing status and payment methods.",
        'technical': "🔧 Technical Issue - Check system logs and API status.",
        'general': "📋 General Support - Standard response time applies."
    }
    
    instruction = team_instructions.get(category, team_instructions['general'])
    
    # Create different message formats
    default_message = f"{instruction}\n\n{base_info}\n\nPlease respond according to your team's SLA."
    
    email_message = f"""Support Ticket Alert - {category.upper()} Team

{instruction}

TICKET DETAILS:
{base_info}

ACTION REQUIRED:
Please log into the support dashboard to respond to this ticket.

---
This is an automated notification from the SaaS Platform Support System.
Do not reply to this email directly.
"""
    
    return {
        'default': default_message,
        'email': email_message
    }