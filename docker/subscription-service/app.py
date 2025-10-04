from flask import Flask, request, jsonify
import psycopg2
import boto3
import json
import bcrypt
import jwt
import uuid
import sys
from datetime import datetime, timedelta
import os
from functools import wraps
import logging
import psycopg2

# Add shared utilities to path
sys.path.append('/app/shared')
from jwt_utils import token_required, get_current_user
from cache_utils import get_valkey_client, cache_key, tenant_cache_key

def handle_errors(f):
    """Decorator for consistent error handling across all endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except psycopg2.OperationalError as e:
            logger.error(f"Database connection error in {f.__name__}: {e}")
            return jsonify({'success': False, 'error': 'Database connection failed. Please try again.'}), 503
        except psycopg2.IntegrityError as e:
            logger.error(f"Database integrity error in {f.__name__}: {e}")
            return jsonify({'success': False, 'error': 'Data integrity error. Please check your input.'}), 400
        except ValueError as e:
            logger.error(f"Validation error in {f.__name__}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Unexpected error in {f.__name__}: {e}")
            return jsonify({'success': False, 'error': 'An unexpected error occurred. Please try again.'}), 500
    return decorated_function

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Get region from environment
AWS_REGION = os.environ.get('AWS_DEFAULT_REGION', 'eu-west-2')

# AWS clients
ssm = boto3.client('ssm', region_name=AWS_REGION)
secrets = boto3.client('secretsmanager', region_name=AWS_REGION)
cognito = boto3.client('cognito-idp', region_name=AWS_REGION)

def get_db_connection(max_retries=3, retry_delay=1):
    """Get database connection with connection pooling via RDS Proxy and retry logic"""
    import time
    
    for attempt in range(max_retries):
        try:
            # Get DB credentials from Secrets Manager
            secret_response = secrets.get_secret_value(SecretId='saas-platform/database/password')
            secret = json.loads(secret_response['SecretString'])
            
            # Get DB endpoint from SSM (RDS Proxy endpoint)
            db_endpoint = ssm.get_parameter(Name='/saas-platform/database/endpoint')['Parameter']['Value']
            db_name = ssm.get_parameter(Name='/saas-platform/database/name')['Parameter']['Value']
            
            # Create connection with proper error handling
            conn = psycopg2.connect(
                host=db_endpoint.split(':')[0],
                database=db_name,
                user=secret['username'],
                password=secret['password'],
                connect_timeout=30,
                application_name='subscription-service'
            )
            
            # Test the connection
            with conn.cursor() as cur:
                cur.execute('SELECT 1')
                cur.fetchone()
            
            logger.info(f"Database connection established on attempt {attempt + 1}")
            return conn
            
        except psycopg2.OperationalError as e:
            logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
            else:
                logger.error(f"All {max_retries} database connection attempts failed")
                raise
        except Exception as e:
            logger.error(f"Unexpected database connection error: {e}")
            raise

def cache_get(key):
    """Get value from cache with error handling"""
    try:
        cache = get_valkey_client()
        if cache:
            value = cache.get(key)
            return value.decode('utf-8') if value else None
    except Exception as e:
        logger.warning(f"Cache get failed for key {key}: {e}")
    return None

def cache_set(key, value, ttl=900):  # 15 minutes default TTL
    """Set value in cache with error handling"""
    try:
        cache = get_valkey_client()
        if cache:
            cache.setex(key, ttl, value)
    except Exception as e:
        logger.warning(f"Cache set failed for key {key}: {e}")

def create_cognito_user(email, password, tenant_id, company_name):
    """Create user in Cognito User Pool"""
    try:
        user_pool_id = os.environ.get('USER_POOL_ID')
        if not user_pool_id:
            user_pool_id = ssm.get_parameter(Name='/saas-platform/auth/user_pool_id')['Parameter']['Value']
        
        # Create user in Cognito
        response = cognito.admin_create_user(
            UserPoolId=user_pool_id,
            Username=email,
            UserAttributes=[
                {'Name': 'email', 'Value': email},
                {'Name': 'email_verified', 'Value': 'true'},
                {'Name': 'custom:tenant_id', 'Value': str(tenant_id)},
                {'Name': 'custom:company_name', 'Value': company_name}
            ],
            TemporaryPassword=password,
            MessageAction='SUPPRESS'  # Don't send welcome email
        )
        
        # Set permanent password
        cognito.admin_set_user_password(
            UserPoolId=user_pool_id,
            Username=email,
            Password=password,
            Permanent=True
        )
        
        # Add user to admin group
        try:
            cognito.admin_add_user_to_group(
                UserPoolId=user_pool_id,
                Username=email,
                GroupName='admin'
            )
        except Exception as e:
            logger.warning(f"Could not add user to admin group: {e}")
        
        logger.info(f"Created Cognito user {email} for tenant {tenant_id}")
        return response['User']['Username']
        
    except Exception as e:
        logger.error(f"Failed to create Cognito user: {e}")
        raise

@app.route('/health')
def health():
    """Health check endpoint - lightweight check for load balancer"""
    return jsonify({
        'status': 'healthy',
        'service': 'subscription-service',
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/signup', methods=['POST'])
def simple_signup():
    """Simple signup that sends SNS notification to admin"""
    data = request.json
    
    if not data or not data.get('email') or not data.get('company'):
        return jsonify({'error': 'Email and company required'}), 400
    
    try:
        # Send SNS notification to admin
        sns = boto3.client('sns', region_name=AWS_REGION)
        
        message = {
            "alert": "NEW SUBSCRIPTION REQUEST",
            "email": data['email'],
            "company": data['company'],
            "plan": data.get('plan', 'basic'),
            "phone": data.get('phone', 'Not provided'),
            "message": data.get('message', 'No additional message'),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        sns.publish(
            TopicArn='arn:aws:sns:eu-west-2:981686514879:saas-platform-support-tickets',
            Subject=f"🆕 New Subscription Request: {data['company']}",
            Message=json.dumps(message, indent=2)
        )
        
        return jsonify({
            'success': True,
            'message': 'Subscription request sent! Admin will contact you soon.',
            'email': data['email'],
            'company': data['company']
        })
        
    except Exception as e:
        logger.error(f"Signup notification failed: {e}")
        return jsonify({'error': 'Failed to send request'}), 500

@app.route('/check-subscription', methods=['POST'])
def check_subscription():
    """Check subscription time left for a user - demo version"""
    data = request.json
    
    if not data or not data.get('email'):
        return jsonify({'error': 'Email required'}), 400
    
    # Demo data without database
    demo_users = {
        'admin@democorp.com': {
            'company': 'Demo Corp',
            'plan': 'pro',
            'status': 'active',
            'monthly_cost': 99.00,
            'days_left': 25,
            'expires_on': '2025-10-29'
        },
        'user@testinc.com': {
            'company': 'Test Inc',
            'plan': 'basic',
            'status': 'active',
            'monthly_cost': 29.00,
            'days_left': 15,
            'expires_on': '2025-10-19'
        },
        'readonly@enterpriseltd.com': {
            'company': 'Enterprise Ltd',
            'plan': 'enterprise',
            'status': 'active',
            'monthly_cost': 299.00,
            'days_left': 30,
            'expires_on': '2025-11-03'
        }
    }
    
    user_info = demo_users.get(data['email'])
    if not user_info:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'success': True,
        'email': data['email'],
        **user_info
    })

@app.route('/health/detailed')
def health_detailed():
    """Detailed health check endpoint"""
    health_status = {
        'status': 'healthy',
        'service': 'subscription-service',
        'timestamp': datetime.utcnow().isoformat(),
        'checks': {}
    }
    
    # Test database connection
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT 1')
        cur.close()
        conn.close()
        health_status['checks']['database'] = 'connected'
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        health_status['checks']['database'] = f'error: {str(e)}'
        health_status['status'] = 'degraded'
    
    # Test cache connection
    try:
        cache = get_valkey_client()
        if cache and cache.ping():
            health_status['checks']['cache'] = 'connected'
        else:
            health_status['checks']['cache'] = 'disconnected'
    except Exception as e:
        health_status['checks']['cache'] = f'error: {str(e)}'
    
    health_status['checks']['cognito'] = 'configured'
    
    return jsonify(health_status)

def validate_email(email):
    """Validate email format"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    import re
    if len(password) < 12:
        return False, "Password must be at least 12 characters"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    return True, "Password is valid"

def validate_company_name(company):
    """Validate company name"""
    if not company or len(company.strip()) < 2:
        return False, "Company name must be at least 2 characters"
    if len(company) > 100:
        return False, "Company name must be less than 100 characters"
    # Check for potentially malicious content
    import re
    if re.search(r'[<>"\']', company):
        return False, "Company name contains invalid characters"
    return True, "Company name is valid"

@app.route('/api/subscription/signup', methods=['POST'])
@handle_errors
def signup():
    """User registration and subscription creation with Cognito integration"""
    try:
        data = request.json
        
        # Validate JSON payload exists
        if not data:
            return jsonify({'success': False, 'message': 'Invalid JSON payload'}), 400
        
        # Validate required fields
        required_fields = ['email', 'password', 'company', 'plan']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'message': f'{field} is required'}), 400
        
        # Validate email format
        if not validate_email(data['email']):
            return jsonify({'success': False, 'message': 'Invalid email format'}), 400
        
        # Validate password strength
        password_valid, password_message = validate_password(data['password'])
        if not password_valid:
            return jsonify({'success': False, 'message': password_message}), 400
        
        # Validate company name
        company_valid, company_message = validate_company_name(data['company'])
        if not company_valid:
            return jsonify({'success': False, 'message': company_message}), 400
        
        # Validate plan
        valid_plans = ['basic', 'pro', 'enterprise']
        if data['plan'] not in valid_plans:
            return jsonify({'success': False, 'message': f'Invalid subscription plan. Must be one of: {", ".join(valid_plans)}'}), 400
        
        conn = get_db_connection()
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if email already exists
        cur.execute('SELECT id FROM users WHERE email = %s', (data['email'],))
        if cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Email already registered'}), 400
        
        # Create tenant
        cur.execute('''
            INSERT INTO tenants (company_name, plan, status, created_at) 
            VALUES (%s, %s, %s, %s) RETURNING id
        ''', (data['company'], data['plan'], 'active', datetime.utcnow()))
        tenant_id = cur.fetchone()[0]
        
        # Create user in Cognito
        try:
            cognito_user_id = create_cognito_user(
                data['email'], 
                data['password'], 
                tenant_id, 
                data['company']
            )
        except Exception as e:
            logger.error(f"Cognito user creation failed: {e}")
            # Rollback tenant creation
            cur.execute('DELETE FROM tenants WHERE id = %s', (tenant_id,))
            conn.commit()
            cur.close()
            conn.close()
            return jsonify({'success': False, 'message': f'User creation failed: {str(e)}'}), 500
        
        # Hash password for local storage (backup)
        password_hash = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create user in local database
        cur.execute('''
            INSERT INTO users (tenant_id, email, password_hash, role, cognito_user_id, created_at) 
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
        ''', (tenant_id, data['email'], password_hash, 'admin', cognito_user_id, datetime.utcnow()))
        user_id = cur.fetchone()[0]
        
        # Create subscription
        plan_amounts = {'basic': 29.00, 'pro': 99.00, 'enterprise': 299.00}
        cur.execute('''
            INSERT INTO subscriptions (tenant_id, plan, status, billing_cycle, amount, next_billing_date, created_at) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (tenant_id, data['plan'], 'active', 'monthly', plan_amounts[data['plan']], 
              datetime.utcnow() + timedelta(days=30), datetime.utcnow()))
        
        # Create initial account balance
        cur.execute('''
            INSERT INTO accounts (tenant_id, balance, currency, created_at)
            VALUES (%s, %s, %s, %s)
        ''', (tenant_id, 0.00, 'USD', datetime.utcnow()))
        
        conn.commit()
        cur.close()
        conn.close()
        
        # Clear any cached data for this tenant
        cache_key = tenant_cache_key(tenant_id, 'subscription')
        cache = get_valkey_client()
        if cache:
            cache.delete(cache_key)
        
        logger.info(f"New subscription created for tenant {tenant_id}, user {data['email']}")
        return jsonify({
            'success': True, 
            'message': 'Account created successfully! You can now login with your credentials.',
            'tenant_id': str(tenant_id),
            'user_id': str(user_id),
            'plan': data['plan'],
            'company': data['company']
        })
        
    except Exception as e:
        logger.error(f"Signup failed: {e}")
        # Try to rollback Cognito user if database failed
        try:
            if 'cognito_user_id' in locals():
                user_pool_id = os.environ.get('USER_POOL_ID')
                if not user_pool_id:
                    user_pool_id = ssm.get_parameter(Name='/saas-platform/auth/user_pool_id')['Parameter']['Value']
                cognito.admin_delete_user(UserPoolId=user_pool_id, Username=data['email'])
        except Exception:
            pass  # Best effort cleanup
            
        return jsonify({'success': False, 'message': f'Registration failed: {str(e)}'}), 500

@app.route('/api/subscription/status', methods=['GET'])
@token_required()
@handle_errors
def get_subscription_status():
    """Get subscription status for current tenant"""
    try:
        user_context = get_current_user()
        current_tenant_id = user_context['tenant_id']
        
        # Try cache first
        cache_key = tenant_cache_key(current_tenant_id, 'subscription')
        cached_data = cache_get(cache_key)
        if cached_data:
            return jsonify(json.loads(cached_data))
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute('''
            SELECT t.company_name, t.plan, s.status, s.billing_cycle, s.amount, s.next_billing_date,
                   a.balance, a.currency
            FROM tenants t
            JOIN subscriptions s ON t.id = s.tenant_id
            LEFT JOIN accounts a ON t.id = a.tenant_id
            WHERE t.id = %s
        ''', (current_tenant_id,))
        
        result = cur.fetchone()
        if result:
            subscription_data = {
                'company_name': result[0],
                'plan': result[1],
                'status': result[2],
                'billing_cycle': result[3],
                'amount': float(result[4]),
                'next_billing_date': result[5].isoformat() if result[5] else None,
                'account_balance': float(result[6]) if result[6] else 0.00,
                'currency': result[7] if result[7] else 'USD'
            }
            
            # Cache the result
            cache_set(cache_key, json.dumps(subscription_data), 300)  # 5 minutes
            
            cur.close()
            conn.close()
            return jsonify(subscription_data)
        else:
            cur.close()
            conn.close()
            return jsonify({'error': 'Subscription not found'}), 404
            
    except Exception as e:
        logger.error(f"Get subscription status failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/subscription/update', methods=['PUT'])
@token_required()
@handle_errors
def update_subscription():
    """Update subscription plan"""
    data = request.json
    
    try:
        user_context = get_current_user()
        current_tenant_id = user_context['tenant_id']
        
        # Validate new plan
        valid_plans = ['basic', 'pro', 'enterprise']
        if data.get('plan') not in valid_plans:
            return jsonify({'error': 'Invalid plan'}), 400
        
        plan_amounts = {'basic': 29.00, 'pro': 99.00, 'enterprise': 299.00}
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get current plan for comparison
        cur.execute('SELECT plan FROM subscriptions WHERE tenant_id = %s', (current_tenant_id,))
        current_plan = cur.fetchone()
        if not current_plan:
            cur.close()
            conn.close()
            return jsonify({'error': 'Subscription not found'}), 404
        
        new_plan = data['plan']
        old_plan = current_plan[0]
        
        # Update subscription
        cur.execute('''
            UPDATE subscriptions 
            SET plan = %s, amount = %s, updated_at = %s
            WHERE tenant_id = %s
        ''', (new_plan, plan_amounts[new_plan], datetime.utcnow(), current_tenant_id))
        
        # Update tenant
        cur.execute('''
            UPDATE tenants 
            SET plan = %s, updated_at = %s
            WHERE id = %s
        ''', (new_plan, datetime.utcnow(), current_tenant_id))
        
        # Record transaction for plan change
        if old_plan != new_plan:
            amount_diff = plan_amounts[new_plan] - plan_amounts[old_plan]
            transaction_type = 'upgrade' if amount_diff > 0 else 'downgrade'
            
            cur.execute('''
                INSERT INTO transactions (tenant_id, type, amount, description, created_at)
                VALUES (%s, %s, %s, %s, %s)
            ''', (current_tenant_id, transaction_type, abs(amount_diff), 
                  f'Plan changed from {old_plan} to {new_plan}', datetime.utcnow()))
        
        conn.commit()
        cur.close()
        conn.close()
        
        # Clear cache
        cache_key = tenant_cache_key(current_tenant_id, 'subscription')
        cache = get_valkey_client()
        if cache:
            cache.delete(cache_key)
        
        logger.info(f"Subscription updated for tenant {current_tenant_id} from {old_plan} to {new_plan}")
        return jsonify({
            'success': True, 
            'message': f'Subscription updated from {old_plan} to {new_plan}',
            'old_plan': old_plan,
            'new_plan': new_plan,
            'new_amount': plan_amounts[new_plan]
        })
        
    except Exception as e:
        logger.error(f"Update subscription failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/subscription/billing', methods=['GET'])
@token_required()
@handle_errors
def get_billing_history():
    """Get billing history and transactions for current tenant"""
    try:
        user_context = get_current_user()
        current_tenant_id = user_context['tenant_id']
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get subscription history
        cur.execute('''
            SELECT plan, amount, created_at, updated_at
            FROM subscriptions 
            WHERE tenant_id = %s
            ORDER BY created_at DESC
        ''', (current_tenant_id,))
        
        subscription_history = []
        for row in cur.fetchall():
            subscription_history.append({
                'plan': row[0],
                'amount': float(row[1]),
                'created_at': row[2].isoformat(),
                'updated_at': row[3].isoformat() if row[3] else None
            })
        
        # Get transaction history
        cur.execute('''
            SELECT type, amount, description, created_at
            FROM transactions 
            WHERE tenant_id = %s
            ORDER BY created_at DESC
            LIMIT 50
        ''', (current_tenant_id,))
        
        transactions = []
        for row in cur.fetchall():
            transactions.append({
                'type': row[0],
                'amount': float(row[1]),
                'description': row[2],
                'created_at': row[3].isoformat()
            })
        
        # Get current account balance
        cur.execute('''
            SELECT balance, currency
            FROM accounts 
            WHERE tenant_id = %s
        ''', (current_tenant_id,))
        
        account_result = cur.fetchone()
        account_balance = float(account_result[0]) if account_result else 0.00
        currency = account_result[1] if account_result else 'USD'
        
        cur.close()
        conn.close()
        
        return jsonify({
            'subscription_history': subscription_history,
            'transactions': transactions,
            'current_balance': account_balance,
            'currency': currency
        })
        
    except Exception as e:
        logger.error(f"Get billing history failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/subscription/balance', methods=['GET'])
@token_required()
@handle_errors
def get_account_balance():
    """Get current account balance"""
    try:
        user_context = get_current_user()
        current_tenant_id = user_context['tenant_id']
        
        # Try cache first
        cache_key = tenant_cache_key(current_tenant_id, 'balance')
        cached_data = cache_get(cache_key)
        if cached_data:
            return jsonify(json.loads(cached_data))
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute('''
            SELECT balance, currency, updated_at
            FROM accounts 
            WHERE tenant_id = %s
        ''', (current_tenant_id,))
        
        result = cur.fetchone()
        if result:
            balance_data = {
                'balance': float(result[0]),
                'currency': result[1],
                'last_updated': result[2].isoformat() if result[2] else None
            }
            
            # Cache for 1 minute
            cache_set(cache_key, json.dumps(balance_data), 60)
            
            cur.close()
            conn.close()
            return jsonify(balance_data)
        else:
            cur.close()
            conn.close()
            return jsonify({'error': 'Account not found'}), 404
            
    except Exception as e:
        logger.error(f"Get account balance failed: {e}")
        return jsonify({'error': str(e)}), 500

# Initialize demo data
def init_demo_data():
    """Initialize demo data for testing"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if demo data already exists
        cur.execute('SELECT COUNT(*) FROM tenants WHERE company_name LIKE %s', ('Demo%',))
        if cur.fetchone()[0] > 0:
            logger.info("Demo data already exists, skipping initialization")
            cur.close()
            conn.close()
            return
        
        # Create demo tenants and subscriptions
        demo_companies = [
            {'name': 'Demo Corp', 'plan': 'pro', 'email': 'admin@democorp.com'},
            {'name': 'Test Inc', 'plan': 'basic', 'email': 'user@testinc.com'},
            {'name': 'Enterprise Ltd', 'plan': 'enterprise', 'email': 'readonly@enterpriseltd.com'}
        ]
        
        plan_amounts = {'basic': 29.00, 'pro': 99.00, 'enterprise': 299.00}
        
        for company in demo_companies:
            # Create tenant
            cur.execute('''
                INSERT INTO tenants (company_name, plan, status, created_at) 
                VALUES (%s, %s, %s, %s) RETURNING id
            ''', (company['name'], company['plan'], 'active', datetime.utcnow()))
            tenant_id = cur.fetchone()[0]
            
            # Create subscription
            cur.execute('''
                INSERT INTO subscriptions (tenant_id, plan, status, billing_cycle, amount, next_billing_date, created_at) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (tenant_id, company['plan'], 'active', 'monthly', plan_amounts[company['plan']], 
                  datetime.utcnow() + timedelta(days=30), datetime.utcnow()))
            
            # Create account
            cur.execute('''
                INSERT INTO accounts (tenant_id, balance, currency, created_at)
                VALUES (%s, %s, %s, %s)
            ''', (tenant_id, 100.00, 'USD', datetime.utcnow()))
            
            logger.info(f"Created demo tenant: {company['name']} (ID: {tenant_id})")
        
        conn.commit()
        cur.close()
        conn.close()
        logger.info("Demo data initialization completed")
        
    except Exception as e:
        logger.error(f"Error initializing demo data: {e}")

if __name__ == '__main__':
    # Initialize demo data on startup
    init_demo_data()
    app.run(host='0.0.0.0', port=5000, debug=False)