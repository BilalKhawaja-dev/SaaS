from flask import Flask, request, jsonify
import boto3
import json
import jwt
import uuid
import os
import sys
from datetime import datetime
from functools import wraps
import logging

# Add shared utilities to path
sys.path.append('/app/shared')
from jwt_utils import token_required, get_current_user
from cache_utils import get_dax_table

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# AWS clients
dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')
sns = boto3.client('sns', region_name='eu-west-2')
ssm = boto3.client('ssm', region_name='eu-west-2')

def get_table():
    """Get DynamoDB table with DAX acceleration"""
    try:
        return get_dax_table('saas-platform-support-tickets')
    except Exception as e:
        logger.error(f"Could not get DAX table: {e}")
        # Fallback to direct DynamoDB
        return dynamodb.Table('saas-platform-support-tickets')

def send_urgent_notification(ticket_data):
    """Send SNS notification for urgent tickets"""
    try:
        # Get SNS topic ARN from environment or SSM
        topic_arn = os.environ.get('SNS_TOPIC_ARN')
        if not topic_arn:
            try:
                response = ssm.get_parameter(Name='/saas-platform/notifications/topic_arn')
                topic_arn = response['Parameter']['Value']
            except Exception as e:
                logger.error(f"Could not get SNS topic ARN: {e}")
                return False
        
        message = {
            "alert": "URGENT SUPPORT TICKET CREATED",
            "ticket_id": ticket_data['ticket_id'],
            "subject": ticket_data['subject'],
            "description": ticket_data['description'],
            "tenant_id": ticket_data['tenant_id'],
            "created_by": ticket_data.get('created_by', 'Unknown'),
            "created_at": ticket_data['created_at'],
            "priority": "URGENT"
        }
        
        sns.publish(
            TopicArn=topic_arn,
            Subject=f"🚨 URGENT: Support Ticket #{ticket_data['ticket_id'][:8]}",
            Message=json.dumps(message, indent=2),
            MessageAttributes={
                'priority': {
                    'DataType': 'String',
                    'StringValue': 'urgent'
                },
                'ticket_id': {
                    'DataType': 'String',
                    'StringValue': ticket_data['ticket_id']
                }
            }
        )
        
        logger.info(f"Urgent notification sent for ticket {ticket_data['ticket_id']}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send urgent notification: {e}")
        return False

@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        # Test DynamoDB/DAX connection
        table = get_table()
        # Simple table description to test connectivity
        table.table_status
        
        return jsonify({
            'status': 'healthy',
            'service': 'support-service',
            'dynamodb': 'connected',
            'dax': 'available',
            'sns': 'configured',
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route('/api/support/tickets', methods=['GET'])
@token_required()
def get_tickets():
    """Get support tickets for current tenant"""
    try:
        user_context = get_current_user()
        if not user_context:
            return jsonify({'error': 'Authentication required'}), 401
        
        tenant_id = user_context.get('tenant_id')
        if not tenant_id:
            return jsonify({'error': 'Tenant ID not found in token'}), 400
        
        table = get_table()
        
        # Query tickets for the tenant with proper partition key
        response = table.query(
            KeyConditionExpression='tenant_id = :tenant_id',
            ExpressionAttributeValues={':tenant_id': tenant_id},
            ScanIndexForward=False  # Sort by sort key descending (newest first)
        )
        
        tickets = []
        for item in response['Items']:
            tickets.append({
                'id': item['ticket_id'],
                'subject': item['subject'],
                'description': item['description'],
                'status': item['status'],
                'priority': item.get('priority', 'medium'),
                'created_by': item.get('created_by', user_context.get('user_id')),
                'created_at': item['created_at'],
                'updated_at': item.get('updated_at', item['created_at'])
            })
        
        logger.info(f"Retrieved {len(tickets)} tickets for tenant {tenant_id}")
        return jsonify({'tickets': tickets})
        
    except Exception as e:
        logger.error(f"Get tickets failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/support/tickets', methods=['POST'])
@token_required()
def create_ticket():
    """Create a new support ticket"""
    try:
        user_context = get_current_user()
        if not user_context:
            return jsonify({'error': 'Authentication required'}), 401
        
        tenant_id = user_context.get('tenant_id')
        user_id = user_context.get('user_id')
        
        if not tenant_id:
            return jsonify({'error': 'Tenant ID not found in token'}), 400
        
        data = request.json
        
        # Validate required fields
        if not data.get('subject') or not data.get('description'):
            return jsonify({'error': 'Subject and description are required'}), 400
        
        # Validate priority
        valid_priorities = ['low', 'medium', 'high', 'urgent']
        priority = data.get('priority', 'medium')
        if priority not in valid_priorities:
            return jsonify({'error': f'Priority must be one of: {", ".join(valid_priorities)}'}), 400
        
        table = get_table()
        ticket_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        item = {
            'tenant_id': tenant_id,
            'ticket_id': ticket_id,
            'subject': data['subject'],
            'description': data['description'],
            'status': 'open',
            'priority': priority,
            'created_by': user_id,
            'created_at': timestamp,
            'updated_at': timestamp
        }
        
        # Store ticket in DynamoDB
        table.put_item(Item=item)
        
        # Send urgent notification if priority is urgent
        notification_sent = False
        if priority == 'urgent':
            notification_sent = send_urgent_notification(item)
        
        logger.info(f"Created {priority} priority ticket {ticket_id} for tenant {tenant_id}")
        
        response_message = 'Ticket created successfully'
        if priority == 'urgent':
            response_message += '. Urgent notification sent to support team!' if notification_sent else '. Note: Urgent notification failed to send.'
        
        return jsonify({
            'success': True, 
            'ticket_id': ticket_id,
            'message': response_message,
            'priority': priority,
            'urgent_notification_sent': notification_sent if priority == 'urgent' else None
        })
        
    except Exception as e:
        logger.error(f"Create ticket failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/support/tickets/<ticket_id>', methods=['GET'])
@token_required()
def get_ticket(ticket_id):
    """Get a specific support ticket"""
    try:
        user_context = get_current_user()
        if not user_context:
            return jsonify({'error': 'Authentication required'}), 401
        
        tenant_id = user_context.get('tenant_id')
        if not tenant_id:
            return jsonify({'error': 'Tenant ID not found in token'}), 400
        
        table = get_table()
        
        response = table.get_item(
            Key={
                'tenant_id': tenant_id,
                'ticket_id': ticket_id
            }
        )
        
        if 'Item' not in response:
            return jsonify({'error': 'Ticket not found'}), 404
        
        item = response['Item']
        ticket = {
            'id': item['ticket_id'],
            'subject': item['subject'],
            'description': item['description'],
            'status': item['status'],
            'priority': item.get('priority', 'medium'),
            'created_by': item.get('created_by', user_context.get('user_id')),
            'created_at': item['created_at'],
            'updated_at': item.get('updated_at', item['created_at'])
        }
        
        return jsonify({'ticket': ticket})
        
    except Exception as e:
        logger.error(f"Get ticket failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/support/tickets/<ticket_id>/status', methods=['PUT'])
@token_required()
def update_ticket_status(ticket_id):
    """Update ticket status"""
    try:
        user_context = get_current_user()
        if not user_context:
            return jsonify({'error': 'Authentication required'}), 401
        
        tenant_id = user_context.get('tenant_id')
        if not tenant_id:
            return jsonify({'error': 'Tenant ID not found in token'}), 400
        
        data = request.json
        
        # Validate status
        valid_statuses = ['open', 'in_progress', 'resolved', 'closed']
        if data.get('status') not in valid_statuses:
            return jsonify({'error': f'Status must be one of: {", ".join(valid_statuses)}'}), 400
        
        table = get_table()
        
        # Update the ticket
        response = table.update_item(
            Key={
                'tenant_id': tenant_id,
                'ticket_id': ticket_id
            },
            UpdateExpression='SET #status = :status, updated_at = :updated_at, updated_by = :updated_by',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': data['status'],
                ':updated_at': datetime.utcnow().isoformat(),
                ':updated_by': user_context.get('user_id')
            },
            ReturnValues='UPDATED_NEW'
        )
        
        logger.info(f"Updated ticket {ticket_id} status to {data['status']} for tenant {tenant_id}")
        return jsonify({'success': True, 'message': 'Ticket status updated successfully'})
        
    except Exception as e:
        logger.error(f"Update ticket status failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/support/tickets/<ticket_id>', methods=['PUT'])
@token_required()
def update_ticket(ticket_id):
    """Update ticket details"""
    try:
        user_context = get_current_user()
        if not user_context:
            return jsonify({'error': 'Authentication required'}), 401
        
        tenant_id = user_context.get('tenant_id')
        if not tenant_id:
            return jsonify({'error': 'Tenant ID not found in token'}), 400
        
        data = request.json
        table = get_table()
        
        # Build update expression dynamically
        update_expression = "SET updated_at = :updated_at, updated_by = :updated_by"
        expression_values = {
            ':updated_at': datetime.utcnow().isoformat(),
            ':updated_by': user_context.get('user_id')
        }
        expression_names = {}
        
        if 'subject' in data:
            update_expression += ", subject = :subject"
            expression_values[':subject'] = data['subject']
        
        if 'description' in data:
            update_expression += ", description = :description"
            expression_values[':description'] = data['description']
        
        if 'priority' in data:
            valid_priorities = ['low', 'medium', 'high', 'urgent']
            if data['priority'] in valid_priorities:
                update_expression += ", priority = :priority"
                expression_values[':priority'] = data['priority']
            else:
                return jsonify({'error': f'Priority must be one of: {", ".join(valid_priorities)}'}), 400
        
        if 'status' in data:
            valid_statuses = ['open', 'in_progress', 'resolved', 'closed']
            if data['status'] in valid_statuses:
                update_expression += ", #status = :status"
                expression_names['#status'] = 'status'
                expression_values[':status'] = data['status']
            else:
                return jsonify({'error': f'Status must be one of: {", ".join(valid_statuses)}'}), 400
        
        # Update the ticket
        update_params = {
            'Key': {
                'tenant_id': tenant_id,
                'ticket_id': ticket_id
            },
            'UpdateExpression': update_expression,
            'ExpressionAttributeValues': expression_values,
            'ReturnValues': 'UPDATED_NEW'
        }
        
        if expression_names:
            update_params['ExpressionAttributeNames'] = expression_names
        
        response = table.update_item(**update_params)
        
        logger.info(f"Updated ticket {ticket_id} for tenant {tenant_id}")
        return jsonify({'success': True, 'message': 'Ticket updated successfully'})
        
    except Exception as e:
        logger.error(f"Update ticket failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/support/tickets/<ticket_id>', methods=['DELETE'])
@token_required()
def delete_ticket(ticket_id):
    """Delete a support ticket"""
    try:
        user_context = get_current_user()
        if not user_context:
            return jsonify({'error': 'Authentication required'}), 401
        
        tenant_id = user_context.get('tenant_id')
        if not tenant_id:
            return jsonify({'error': 'Tenant ID not found in token'}), 400
        
        # Check if user has admin role for deletion
        user_groups = user_context.get('groups', [])
        if 'admin' not in user_groups:
            return jsonify({'error': 'Admin role required to delete tickets'}), 403
        
        table = get_table()
        
        table.delete_item(
            Key={
                'tenant_id': tenant_id,
                'ticket_id': ticket_id
            }
        )
        
        logger.info(f"Deleted ticket {ticket_id} for tenant {tenant_id}")
        return jsonify({'success': True, 'message': 'Ticket deleted successfully'})
        
    except Exception as e:
        logger.error(f"Delete ticket failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Initialize with demo data if needed
def init_demo_data():
    """Initialize demo data for testing"""
    try:
        table = get_table()
        
        # Demo tenant IDs (these would come from your subscription service)
        demo_tenants = [
            'demo-tenant-1',
            'demo-tenant-2',
            'demo-tenant-3'
        ]
        
        demo_tickets = [
            {
                'subject': 'Login Issues', 
                'description': 'Cannot access my account after password reset', 
                'status': 'open',
                'priority': 'high'
            },
            {
                'subject': 'Billing Question', 
                'description': 'Need clarification on recent charges', 
                'status': 'in_progress',
                'priority': 'medium'
            },
            {
                'subject': 'Feature Request', 
                'description': 'Would like to see analytics dashboard with more metrics', 
                'status': 'resolved',
                'priority': 'low'
            },
        ]
        
        for tenant_id in demo_tenants:
            for ticket_data in demo_tickets:
                ticket_id = str(uuid.uuid4())
                timestamp = datetime.utcnow().isoformat()
                
                item = {
                    'tenant_id': tenant_id,
                    'ticket_id': ticket_id,
                    'subject': ticket_data['subject'],
                    'description': ticket_data['description'],
                    'status': ticket_data['status'],
                    'priority': ticket_data['priority'],
                    'created_by': 'demo-user',
                    'created_at': timestamp,
                    'updated_at': timestamp
                }
                
                # Check if ticket already exists to avoid duplicates
                try:
                    existing = table.get_item(Key={'tenant_id': tenant_id, 'ticket_id': ticket_id})
                    if 'Item' not in existing:
                        table.put_item(Item=item)
                except Exception:
                    # If get_item fails, try to put anyway
                    table.put_item(Item=item)
                    
        logger.info("Demo data initialization completed")
                    
    except Exception as e:
        logger.error(f"Error initializing demo data: {e}")

if __name__ == '__main__':
    # Initialize demo data on startup
    init_demo_data()
    app.run(host='0.0.0.0', port=5001, debug=False)