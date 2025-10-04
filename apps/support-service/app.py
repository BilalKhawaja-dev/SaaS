from flask import Flask, request, jsonify
import boto3
import json
import jwt
import uuid
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__)

# AWS clients
dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')
ssm = boto3.client('ssm', region_name='eu-west-2')
secrets = boto3.client('secretsmanager', region_name='eu-west-2')

# Get table name from environment or SSM
table_name = os.environ.get('DYNAMODB_TABLE_NAME', 'saas-platform-tickets')
table = dynamodb.Table(table_name)

def get_jwt_secret():
    try:
        secret_response = secrets.get_secret_value(SecretId='saas-platform/jwt/secret')
        secret_data = json.loads(secret_response['SecretString'])
        return secret_data['jwt_secret_key']
    except:
        return os.environ.get('JWT_SECRET_KEY', 'fallback-secret-key')

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            token = token.split(' ')[1]  # Remove 'Bearer ' prefix
            jwt_secret = get_jwt_secret()
            data = jwt.decode(token, jwt_secret, algorithms=['HS256'])
            current_tenant_id = data['tenant_id']
        except Exception as e:
            return jsonify({'message': 'Token is invalid'}), 401
        
        return f(current_tenant_id, *args, **kwargs)
    return decorated

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/api/support/tickets', methods=['GET'])
@token_required
def get_tickets(current_tenant_id):
    try:
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('tenant_id').eq(current_tenant_id),
            ScanIndexForward=False  # Sort by sort key descending
        )
        
        tickets = []
        for item in response['Items']:
            tickets.append({
                'id': item['ticket_id'],
                'subject': item['subject'],
                'description': item['description'],
                'status': item['status'],
                'created_at': item['created_at']
            })
        
        return jsonify({'tickets': tickets})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/support/tickets', methods=['POST'])
@token_required
def create_ticket(current_tenant_id):
    try:
        data = request.json
        ticket_id = str(uuid.uuid4())
        
        item = {
            'tenant_id': current_tenant_id,
            'ticket_id': ticket_id,
            'subject': data['subject'],
            'description': data['description'],
            'status': 'open',
            'created_at': datetime.utcnow().isoformat()
        }
        
        table.put_item(Item=item)
        
        return jsonify({'success': True, 'ticket_id': ticket_id})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/support/tickets/<ticket_id>/status', methods=['PUT'])
@token_required
def update_ticket_status(current_tenant_id, ticket_id):
    try:
        data = request.json
        
        table.update_item(
            Key={
                'tenant_id': current_tenant_id,
                'ticket_id': ticket_id
            },
            UpdateExpression='SET #status = :status',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={':status': data['status']}
        )
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Initialize with demo data
def init_demo_data():
    try:
        # Demo tenant IDs (these would come from your auth service)
        demo_tenants = [
            'demo-tenant-1',
            'demo-tenant-2',
            'demo-tenant-3'
        ]
        
        demo_tickets = [
            {'subject': 'Login Issues', 'description': 'Cannot access my account', 'status': 'open'},
            {'subject': 'Billing Question', 'description': 'Need clarification on charges', 'status': 'in_progress'},
            {'subject': 'Feature Request', 'description': 'Would like to see analytics dashboard', 'status': 'closed'},
        ]
        
        for tenant_id in demo_tenants:
            for ticket_data in demo_tickets:
                ticket_id = str(uuid.uuid4())
                item = {
                    'tenant_id': tenant_id,
                    'ticket_id': ticket_id,
                    'subject': ticket_data['subject'],
                    'description': ticket_data['description'],
                    'status': ticket_data['status'],
                    'created_at': datetime.utcnow().isoformat()
                }
                
                # Check if ticket already exists to avoid duplicates
                try:
                    table.get_item(Key={'tenant_id': tenant_id, 'ticket_id': ticket_id})
                except:
                    table.put_item(Item=item)
                    
    except Exception as e:
        print(f"Error initializing demo data: {e}")

if __name__ == '__main__':
    init_demo_data()
    app.run(host='0.0.0.0', port=5001)