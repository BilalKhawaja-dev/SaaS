import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """
    Cognito Pre Token Generation Lambda Trigger
    Adds custom claims to JWT tokens including tenant_id and groups
    """
    try:
        logger.info(f"Token customizer event: {json.dumps(event)}")
        
        # Get user attributes
        user_attributes = event.get('request', {}).get('userAttributes', {})
        group_configuration = event.get('request', {}).get('groupConfiguration', {})
        
        # Extract custom attributes
        tenant_id = user_attributes.get('custom:tenant_id', '')
        company_name = user_attributes.get('custom:company_name', '')
        
        # Get user groups
        groups_to_override = group_configuration.get('groupsToOverride', [])
        
        # Add custom claims to the token
        claims_to_add = {
            'tenant_id': tenant_id,
            'company_name': company_name
        }
        
        # Add groups as a claim
        if groups_to_override:
            claims_to_add['cognito:groups'] = groups_to_override
        
        # Set the claims in the response
        event['response'] = {
            'claimsOverrideDetails': {
                'claimsToAddOrOverride': claims_to_add
            }
        }
        
        logger.info(f"Added custom claims: {claims_to_add}")
        return event
        
    except Exception as e:
        logger.error(f"Token customization failed: {str(e)}")
        # Return the event unchanged if there's an error
        return event