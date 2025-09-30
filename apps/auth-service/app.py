from flask import Flask, request, jsonify
import psycopg2
import boto3
import json
import bcrypt
import jwt
import uuid
from datetime import datetime, timedelta
import os
from functools import wraps

app = Flask(__name__)

# AWS clients
ssm = boto3.client('ssm', region_name='eu-west-2')
secrets = boto3.client('secretsmanager', region_name='eu-west-2')

def get_db_connection():
    # Get DB credentials from Secrets Manager
    secret_response = secrets.get_secret_value(SecretId='saas-platform/database/password')
    secret = json.loads(secret_response['SecretString'])
    
    # Get DB endpoint from SSM
    db_endpoint = ssm.get_parameter(Name='/saas-platform/database/endpoint')['Parameter']['Value']
    db_name = ssm.get_parameter(Name='/saas-platform/database/name')['Parameter']['Value']
    
    return psycopg2.connect(
        host=db_endpoint.split(':')[0],
        database=db_name,
        user=secret['username'],
        password=secret['password']
    )

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Create tenants table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS tenants (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_name VARCHAR(255) NOT NULL,
            plan VARCHAR(50) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create users table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID REFERENCES tenants(id),
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create accounts table for balance service
    cur.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID REFERENCES tenants(id),
            balance DECIMAL(10,2) DEFAULT 1000.00,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert demo data
    cur.execute('''
        INSERT INTO tenants (company_name, plan) 
        VALUES ('Demo Corp', 'pro'), ('Test Inc', 'basic'), ('Enterprise Ltd', 'enterprise')
        ON CONFLICT DO NOTHING
    ''')
    
    # Get tenant IDs for demo data
    cur.execute("SELECT id, company_name FROM tenants")
    tenants = cur.fetchall()
    
    for tenant_id, company_name in tenants:
        # Create demo user
        demo_email = f"demo@{company_name.lower().replace(' ', '')}.com"
        password_hash = bcrypt.hashpw('demo123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        cur.execute('''
            INSERT INTO users (tenant_id, email, password_hash) 
            VALUES (%s, %s, %s)
            ON CONFLICT (email) DO NOTHING
        ''', (tenant_id, demo_email, password_hash))
        
        # Create account with demo balance
        cur.execute('''
            INSERT INTO accounts (tenant_id, balance) 
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        ''', (tenant_id, 1000.00 + (hash(company_name) % 5000)))
    
    conn.commit()
    cur.close()
    conn.close()

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.json
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Create tenant
        cur.execute('''
            INSERT INTO tenants (company_name, plan) 
            VALUES (%s, %s) RETURNING id
        ''', (data['company'], data['plan']))
        tenant_id = cur.fetchone()[0]
        
        # Hash password
        password_hash = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create user
        cur.execute('''
            INSERT INTO users (tenant_id, email, password_hash) 
            VALUES (%s, %s, %s)
        ''', (tenant_id, data['email'], password_hash))
        
        # Create account with initial balance
        initial_balance = {'basic': 500, 'pro': 1000, 'enterprise': 5000}[data['plan']]
        cur.execute('''
            INSERT INTO accounts (tenant_id, balance) 
            VALUES (%s, %s)
        ''', (tenant_id, initial_balance))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Account created successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute('''
            SELECT u.id, u.tenant_id, u.password_hash, t.company_name, t.plan
            FROM users u
            JOIN tenants t ON u.tenant_id = t.id
            WHERE u.email = %s
        ''', (data['email'],))
        
        user = cur.fetchone()
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 401
        
        user_id, tenant_id, password_hash, company_name, plan = user
        
        if bcrypt.checkpw(data['password'].encode('utf-8'), password_hash.encode('utf-8')):
            # Generate JWT token
            token = jwt.encode({
                'user_id': str(user_id),
                'tenant_id': str(tenant_id),
                'exp': datetime.utcnow() + timedelta(hours=24)
            }, 'your-secret-key', algorithm='HS256')
            
            return jsonify({
                'success': True,
                'token': token,
                'user': {
                    'id': str(user_id),
                    'tenant_id': str(tenant_id),
                    'company': company_name,
                    'plan': plan
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Invalid password'}), 401
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

@app.route('/api/auth/validate', methods=['POST'])
def validate_token():
    """Validate JWT token - used by other services"""
    try:
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'valid': False, 'message': 'No token provided'}), 401
        
        if token.startswith('Bearer '):
            token = token[7:]
        
        payload = jwt.decode(token, 'your-secret-key', algorithms=['HS256'])
        
        return jsonify({
            'valid': True,
            'user_id': payload['user_id'],
            'tenant_id': payload['tenant_id']
        })
        
    except jwt.ExpiredSignatureError:
        return jsonify({'valid': False, 'message': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'valid': False, 'message': 'Invalid token'}), 401
    except Exception as e:
        return jsonify({'valid': False, 'message': str(e)}), 400

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)