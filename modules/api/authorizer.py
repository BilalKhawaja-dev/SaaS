import json
import jwt
import os
import requests
from jwt import PyJWKClient
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    try:
        logger.info(f"Authorizer event: {json.dumps(event)}")
        
        # Extract token from Authorization header
        headers = event.get('headers', {})
        # Handle case-insensitive headers
        auth_header = headers.get('Authorization') or headers.get('authorization', '')
        
        if not auth_header:
            logger.error("No Authorization header found")
            return generate_deny_policy('No Authorization header')
        
        if not auth_header.startswith('Bearer '):
            logger.error("Invalid Authorization header format")
            return generate_deny_policy('Invalid Authorization header format')
        
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        # Get user pool info from environment variables
        user_pool_id = os.environ.get('USER_POOL_ID')
        client_id = os.environ.get('CLIENT_ID')
        region = os.environ.get('REGION', 'eu-west-2')
        
        if not user_pool_id or not client_id:
            logger.error("Missing environment variables")
            return generate_deny_policy('Missing configuration')
        
        # Verify JWT token with Cognito JWKS
        jwks_url = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json"
        logger.info(f"Using JWKS URL: {jwks_url}")
        
        jwks_client = PyJWKClient(jwks_url)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        # Decode and verify token
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=client_id,
            options={"verify_exp": True}
        )
        
        logger.info(f"Token payload: {json.dumps(payload, default=str)}")
        
        # Extract user info
        username = payload.get('cognito:username', payload.get('username', ''))
        groups = payload.get('cognito:groups', [])
        user_id = payload.get('sub', '')
        email = payload.get('email', '')
        
        # Extract method and resource for permission checking
        method = event.get('httpMethod', '')
        method_arn = event.get('methodArn', '')
        
        # Generate resource ARN pattern for policy
        # Convert specific method ARN to wildcard pattern for the API
        arn_parts = method_arn.split('/')
        if len(arn_parts) >= 3:
            # Format: arn:aws:execute-api:region:account:api-id/stage/method/resource
            base_arn = '/'.join(arn_parts[:3])  # Get base ARN up to stage
            resource_pattern = f"{base_arn}/*"
        else:
            resource_pattern = method_arn
        
        # Determine permissions based on groups
        effect = 'Deny'  # Default deny
        
        if 'admin' in groups:
            effect = 'Allow'
            logger.info(f"Admin access granted for user: {username}")
        elif 'user' in groups or 'readonly' in groups:
            # Allow GET and OPTIONS for regular users
            if method in ['GET', 'OPTIONS']:
                effect = 'Allow'
                logger.info(f"Read access granted for user: {username}, method: {method}")
            else:
                logger.info(f"Write access denied for user: {username}, method: {method}")
        else:
            logger.info(f"No valid groups found for user: {username}, groups: {groups}")
        
        # Generate IAM policy
        policy = {
            'principalId': user_id,
            'policyDocument': {
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Action': 'execute-api:Invoke',
                        'Effect': effect,
                        'Resource': resource_pattern
                    }
                ]
            },
            'context': {
                'username': username,
                'groups': ','.join(groups),
                'user_id': user_id,
                'email': email,
                'tenant_id': payload.get('custom:tenant_id', '')
            }
        }
        
        logger.info(f"Generated policy: {json.dumps(policy)}")
        return policy
        
    except jwt.ExpiredSignatureError:
        logger.error("Token has expired")
        return generate_deny_policy('Token expired')
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid token: {str(e)}")
        return generate_deny_policy('Invalid token')
    except Exception as e:
        logger.error(f"Authorization failed: {str(e)}")
        return generate_deny_policy('Authorization failed')

def generate_deny_policy(reason):
    """Generate a deny policy for unauthorized requests"""
    return {
        'principalId': 'unauthorized',
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:Invoke',
                    'Effect': 'Deny',
                    'Resource': '*'
                }
            ]
        },
        'context': {
            'reason': reason
        }
    }