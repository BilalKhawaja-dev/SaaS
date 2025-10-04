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

def handle_errors(f):
    """Decorator for consistent error handling across all endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {f.__name__}: {e}")
            return jsonify({'success': False, 'error': 'An unexpected error occurred. Please try again.'}), 500
    return decorated_function

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Get region from environment
AWS_REGION = os.environ.get('AWS_DEFAULT_REGION', 'eu-west-2')

# AWS clients
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
sns = boto3.client('sns', region_name=AWS_REGION)
ssm = boto3.client('ssm', region_name=AWS_REGION)

def get_table():
    """Get DynamoDB table with DAX acceleration"""
    try:
        # Get table name from environment or SSM
        table_name = os.environ.get('DYNAMODB_TABLE_NAME')
        if not table_name:
            try:
                response = ssm.get_parameter(Name='/saas-platform/dynamodb/tickets_table_name')
                table_name = response['Parameter']['Value']
            except Exception as e:
                logger.warning(f"Could not get table name from SSM: {e}")
                table_name = 'saas-platform-tickets'  # Fallback
        
        return get_dax_table(table_name)
    except Exception as e:
        logger.error(f"Could not get DAX table: {e}")
        # Fallback to direct DynamoDB
        table_name = os.environ.get('DYNAMODB_TABLE_NAME', 'saas-platform-tickets')
        return dynamodb.Table(table_name)

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
    """Health check endpoint - lightweight check for load balancer"""
    return jsonify({
        'status': 'healthy',
        'service': 'support-service',
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/create-ticket', methods=['POST'])
def create_ticket_simple():
    """Simple ticket creation without auth for demo"""
    data = request.json
    
    if not data or not data.get('subject') or not data.get('description'):
        return jsonify({'error': 'Subject and description required'}), 400
    
    try:
        table = get_table()
        ticket_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        # Use demo tenant ID
        demo_tenant_id = 'demo-tenant-123'
        
        item = {
            'tenant_id': demo_tenant_id,
            'ticket_id': ticket_id,
            'subject': data['subject'],
            'description': data['description'],
            'status': 'open',
            'priority': data.get('priority', 'medium'),
            'created_by': data.get('email', 'demo-user'),
            'created_at': timestamp,
            'updated_at': timestamp
        }
        
        table.put_item(Item=item)
        
        return jsonify({
            'success': True,
            'ticket_id': ticket_id,
            'message': 'Ticket created successfully'
        })
        
    except Exception as e:
        logger.error(f"Create ticket failed: {e}")
        return jsonify({'error': 'Failed to create ticket'}), 500

@app.route('/health/detailed')
def health_detailed():
    """Detailed health check endpoint"""
    health_status = {
        'status': 'healthy',
        'service': 'support-service',
        'timestamp': datetime.utcnow().isoformat(),
        'checks': {}
    }
    
    # Test DynamoDB/DAX connection
    try:
        table = get_table()
        table.table_status
        health_status['checks']['dynamodb'] = 'connected'
    except Exception as e:
        logger.warning(f"DynamoDB health check failed: {e}")
        health_status['checks']['dynamodb'] = f'error: {str(e)}'
        health_status['status'] = 'degraded'
    
    # Test SNS configuration
    try:
        topic_arn = os.environ.get('SNS_TOPIC_ARN')
        if topic_arn:
            health_status['checks']['sns'] = 'configured'
        else:
            health_status['checks']['sns'] = 'not_configured'
    except Exception as e:
        health_status['checks']['sns'] = f'error: {str(e)}'
    
    return jsonify(health_status)

@app.route('/api/support/tickets', methods=['GET'])
@token_required()
@handle_errors
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
@handle_errors
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

if __name__ == '__main__':
    # Start the application
    logger.info("Starting support service on port 5001")
    app.run(host='0.0.0.0', port=5001, debug=False)