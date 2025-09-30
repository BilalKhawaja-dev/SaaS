from flask import Flask, request, jsonify
import psycopg2
import boto3
import json
import jwt
from functools import wraps

app = Flask(__name__)

# AWS clients
ssm = boto3.client('ssm', region_name='eu-west-2')
secrets = boto3.client('secretsmanager', region_name='eu-west-2')

def get_db_connection():
    secret_response = secrets.get_secret_value(SecretId='saas-platform/database/password')
    secret = json.loads(secret_response['SecretString'])
    
    db_endpoint = ssm.get_parameter(Name='/saas-platform/database/endpoint')['Parameter']['Value']
    db_name = ssm.get_parameter(Name='/saas-platform/database/name')['Parameter']['Value']
    
    return psycopg2.connect(
        host=db_endpoint.split(':')[0],
        database=db_name,
        user=secret['username'],
        password=secret['password']
    )

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            token = token.split(' ')[1]  # Remove 'Bearer ' prefix
            data = jwt.decode(token, 'your-secret-key', algorithms=['HS256'])
            current_tenant_id = data['tenant_id']
        except:
            return jsonify({'message': 'Token is invalid'}), 401
        
        return f(current_tenant_id, *args, **kwargs)
    return decorated

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/api/balance', methods=['GET'])
@token_required
def get_balance(current_tenant_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute('''
            SELECT balance FROM accounts WHERE tenant_id = %s
        ''', (current_tenant_id,))
        
        result = cur.fetchone()
        if result:
            balance = float(result[0])
            return jsonify({'balance': balance})
        else:
            return jsonify({'balance': 0.00})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

@app.route('/api/balance/transactions', methods=['GET'])
@token_required
def get_transactions(current_tenant_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Create transactions table if it doesn't exist
        cur.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID REFERENCES tenants(id),
                amount DECIMAL(10,2) NOT NULL,
                description VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert some demo transactions if none exist
        cur.execute('SELECT COUNT(*) FROM transactions WHERE tenant_id = %s', (current_tenant_id,))
        if cur.fetchone()[0] == 0:
            demo_transactions = [
                (-50.00, 'Monthly subscription fee'),
                (100.00, 'Account credit'),
                (-25.00, 'API usage charges'),
                (-15.00, 'Storage fees')
            ]
            for amount, desc in demo_transactions:
                cur.execute('''
                    INSERT INTO transactions (tenant_id, amount, description)
                    VALUES (%s, %s, %s)
                ''', (current_tenant_id, amount, desc))
        
        cur.execute('''
            SELECT amount, description, created_at 
            FROM transactions 
            WHERE tenant_id = %s 
            ORDER BY created_at DESC 
            LIMIT 10
        ''', (current_tenant_id,))
        
        transactions = []
        for row in cur.fetchall():
            transactions.append({
                'amount': float(row[0]),
                'description': row[1],
                'created_at': row[2].isoformat()
            })
        
        conn.commit()
        return jsonify({'transactions': transactions})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)