import json
import jwt
import requests
from jwt import PyJWKClient

def handler(event, context):
    try:
        # Extract token from Authorization header
        token = event.get('headers', {}).get('Authorization', '')
        if token.startswith('Bearer '):
            token = token[7:]
        
        # Get user pool info from environment
        user_pool_id = event['requestContext']['authorizer']['user_pool_id']
        region = event['requestContext']['authorizer']['region']
        
        # Verify JWT token with Cognito
        jwks_url = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json"
        jwks_client = PyJWKClient(jwks_url)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        # Decode and verify token
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=event['requestContext']['authorizer']['client_id']
        )
        
        # Extract user info
        username = payload.get('cognito:username', '')
        groups = payload.get('cognito:groups', [])
        
        # Determine permissions based on groups
        if 'admin' in groups:
            effect = 'Allow'
            resource = event['methodArn'].replace('/*', '/*')  # Full access
        elif 'user' in groups or 'readonly' in groups:
            # Check if it's a read operation
            method = event['httpMethod']
            if method in ['GET', 'OPTIONS']:
                effect = 'Allow'
                resource = event['methodArn']
            else:
                effect = 'Deny'
                resource = event['methodArn']
        else:
            effect = 'Deny'
            resource = event['methodArn']
        
        # Generate IAM policy
        policy = {
            'principalId': username,
            'policyDocument': {
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Action': 'execute-api:Invoke',
                        'Effect': effect,
                        'Resource': resource
                    }
                ]
            },
            'context': {
                'username': username,
                'groups': ','.join(groups),
                'user_id': payload.get('sub', ''),
                'email': payload.get('email', '')
            }
        }
        
        return policy
        
    except Exception as e:
        print(f"Authorization failed: {str(e)}")
        # Return deny policy
        return {
            'principalId': 'unauthorized',
            'policyDocument': {
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Action': 'execute-api:Invoke',
                        'Effect': 'Deny',
                        'Resource': event['methodArn']
                    }
                ]
            }
        }