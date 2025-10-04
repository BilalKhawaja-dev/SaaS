"""
Shared JWT utilities for SaaS platform services
Provides consistent JWT validation across all microservices
"""

import jwt
import json
import boto3
import os
import logging
from functools import wraps
from flask import request, jsonify
from jwt import PyJWKClient
import requests

logger = logging.getLogger(__name__)

class JWTValidator:
    def __init__(self):
        self.region = os.environ.get('AWS_DEFAULT_REGION', 'eu-west-2')
        self.secrets_client = boto3.client('secretsmanager', region_name=self.region)
        self.ssm_client = boto3.client('ssm', region_name=self.region)
        self._jwt_secret = None
        self._cognito_jwks_client = None
        
    def get_jwt_secret(self):
        """Get JWT secret from Secrets Manager with caching"""
        if self._jwt_secret is None:
            try:
                secret_response = self.secrets_client.get_secret_value(
                    SecretId='saas-platform/jwt/secret'
                )
                secret_data = json.loads(secret_response['SecretString'])
                self._jwt_secret = secret_data['jwt_secret_key']
            except Exception as e:
                logger.error(f"Failed to get JWT secret: {e}")
                # Fallback to environment variable for development
                self._jwt_secret = os.environ.get('JWT_SECRET_KEY', 'fallback-secret-key')
        return self._jwt_secret
    
    def get_cognito_jwks_client(self):
        """Get Cognito JWKS client with caching"""
        if self._cognito_jwks_client is None:
            try:
                # Get Cognito User Pool ID from environment or SSM
                user_pool_id = os.environ.get('USER_POOL_ID')
                if not user_pool_id:
                    user_pool_id = self.ssm_client.get_parameter(
                        Name='/saas-platform/cognito/user_pool_id'
                    )['Parameter']['Value']
                
                jwks_url = f"https://cognito-idp.{self.region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json"
                self._cognito_jwks_client = PyJWKClient(jwks_url)
            except Exception as e:
                logger.error(f"Failed to initialize Cognito JWKS client: {e}")
                self._cognito_jwks_client = None
        return self._cognito_jwks_client
    
    def validate_cognito_token(self, token):
        """Validate Cognito JWT token"""
        try:
            jwks_client = self.get_cognito_jwks_client()
            if not jwks_client:
                raise Exception("JWKS client not available")
            
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            
            # Get client ID from environment or SSM
            client_id = os.environ.get('CLIENT_ID')
            if not client_id:
                client_id = self.ssm_client.get_parameter(
                    Name='/saas-platform/cognito/client_id'
                )['Parameter']['Value']
            
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=client_id,
                options={"verify_exp": True}
            )
            
            return {
                'valid': True,
                'payload': payload,
                'user_id': payload.get('sub'),
                'tenant_id': payload.get('tenant_id'),
                'email': payload.get('email'),
                'groups': payload.get('cognito:groups', []),
                'company_name': payload.get('company_name', '')
            }
            
        except jwt.ExpiredSignatureError:
            return {'valid': False, 'error': 'Token expired'}
        except jwt.InvalidTokenError as e:
            return {'valid': False, 'error': f'Invalid token: {str(e)}'}
        except Exception as e:
            return {'valid': False, 'error': f'Validation failed: {str(e)}'}
    
    def validate_service_token(self, token):
        """Validate service-to-service JWT token (using shared secret)"""
        try:
            jwt_secret = self.get_jwt_secret()
            payload = jwt.decode(
                token,
                jwt_secret,
                algorithms=['HS256'],
                options={"verify_exp": True}
            )
            
            return {
                'valid': True,
                'payload': payload,
                'user_id': payload.get('user_id'),
                'tenant_id': payload.get('tenant_id'),
                'service': payload.get('service', 'unknown')
            }
            
        except jwt.ExpiredSignatureError:
            return {'valid': False, 'error': 'Token expired'}
        except jwt.InvalidTokenError as e:
            return {'valid': False, 'error': f'Invalid token: {str(e)}'}
        except Exception as e:
            return {'valid': False, 'error': f'Validation failed: {str(e)}'}

# Global validator instance
jwt_validator = JWTValidator()

def token_required(allow_service_tokens=False):
    """
    Decorator for routes that require JWT authentication
    
    Args:
        allow_service_tokens (bool): Whether to allow service-to-service tokens
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return jsonify({'error': 'Authorization header missing'}), 401
            
            if not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Invalid authorization header format'}), 401
            
            token = auth_header[7:]  # Remove 'Bearer ' prefix
            
            # Try Cognito token validation first
            result = jwt_validator.validate_cognito_token(token)
            
            # If Cognito validation fails and service tokens are allowed, try service token
            if not result['valid'] and allow_service_tokens:
                result = jwt_validator.validate_service_token(token)
            
            if not result['valid']:
                return jsonify({'error': result['error']}), 401
            
            # Add user context to request
            request.user_context = {
                'user_id': result.get('user_id'),
                'tenant_id': result.get('tenant_id'),
                'email': result.get('email', ''),
                'groups': result.get('groups', []),
                'company_name': result.get('company_name', ''),
                'is_service_token': 'service' in result
            }
            
            return f(*args, **kwargs)
        return decorated
    return decorator

def require_role(required_roles):
    """
    Decorator to require specific user roles
    
    Args:
        required_roles (list): List of required roles (e.g., ['admin', 'user'])
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not hasattr(request, 'user_context'):
                return jsonify({'error': 'Authentication required'}), 401
            
            user_groups = request.user_context.get('groups', [])
            
            # Check if user has any of the required roles
            if not any(role in user_groups for role in required_roles):
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated
    return decorator

def get_current_user():
    """Get current user context from request"""
    return getattr(request, 'user_context', None)

def generate_service_token(service_name, user_id=None, tenant_id=None, expires_in_hours=1):
    """
    Generate a service-to-service JWT token
    
    Args:
        service_name (str): Name of the service generating the token
        user_id (str): Optional user ID for user context
        tenant_id (str): Optional tenant ID for tenant context
        expires_in_hours (int): Token expiration in hours
    """
    try:
        import datetime
        
        jwt_secret = jwt_validator.get_jwt_secret()
        
        payload = {
            'service': service_name,
            'iat': datetime.datetime.utcnow(),
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=expires_in_hours)
        }
        
        if user_id:
            payload['user_id'] = user_id
        if tenant_id:
            payload['tenant_id'] = tenant_id
        
        return jwt.encode(payload, jwt_secret, algorithm='HS256')
        
    except Exception as e:
        logger.error(f"Failed to generate service token: {e}")
        return None