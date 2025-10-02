"""
Shared caching utilities for SaaS platform services
Provides consistent caching interface for Valkey (Redis) and DAX
"""

import redis
import boto3
import json
import logging
import os
from typing import Optional, Any, Dict

logger = logging.getLogger(__name__)

class ValkeyCache:
    """Valkey (Redis) cache client with connection pooling and error handling"""
    
    def __init__(self):
        self.ssm_client = boto3.client('ssm', region_name='eu-west-2')
        self._redis_client = None
        self._reader_client = None
        
    def get_client(self, read_only=False):
        """Get Redis client with connection pooling"""
        try:
            if read_only and self._reader_client is None:
                endpoint = self._get_reader_endpoint()
                port = self._get_port()
                self._reader_client = redis.Redis(
                    host=endpoint,
                    port=port,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
            elif not read_only and self._redis_client is None:
                endpoint = self._get_primary_endpoint()
                port = self._get_port()
                self._redis_client = redis.Redis(
                    host=endpoint,
                    port=port,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
            
            return self._reader_client if read_only else self._redis_client
            
        except Exception as e:
            logger.error(f"Failed to create Redis client: {e}")
            return None
    
    def _get_primary_endpoint(self):
        """Get primary Valkey endpoint from SSM"""
        try:
            response = self.ssm_client.get_parameter(
                Name='/saas-platform/cache/valkey/endpoint'
            )
            return response['Parameter']['Value']
        except Exception as e:
            logger.error(f"Failed to get Valkey endpoint: {e}")
            return os.environ.get('VALKEY_ENDPOINT', 'localhost')
    
    def _get_reader_endpoint(self):
        """Get reader Valkey endpoint from SSM"""
        try:
            response = self.ssm_client.get_parameter(
                Name='/saas-platform/cache/valkey/reader_endpoint'
            )
            return response['Parameter']['Value']
        except Exception as e:
            logger.warning(f"Failed to get Valkey reader endpoint: {e}")
            return self._get_primary_endpoint()  # Fallback to primary
    
    def _get_port(self):
        """Get Valkey port from SSM"""
        try:
            response = self.ssm_client.get_parameter(
                Name='/saas-platform/cache/valkey/port'
            )
            return int(response['Parameter']['Value'])
        except Exception as e:
            logger.error(f"Failed to get Valkey port: {e}")
            return 6379
    
    def get(self, key: str, use_reader=True) -> Optional[str]:
        """Get value from cache"""
        try:
            client = self.get_client(read_only=use_reader)
            if client:
                return client.get(key)
        except Exception as e:
            logger.warning(f"Cache get failed for key {key}: {e}")
        return None
    
    def set(self, key: str, value: str, ttl: int = 900) -> bool:
        """Set value in cache with TTL (default 15 minutes)"""
        try:
            client = self.get_client(read_only=False)
            if client:
                return client.setex(key, ttl, value)
        except Exception as e:
            logger.warning(f"Cache set failed for key {key}: {e}")
        return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            client = self.get_client(read_only=False)
            if client:
                return bool(client.delete(key))
        except Exception as e:
            logger.warning(f"Cache delete failed for key {key}: {e}")
        return False
    
    def get_json(self, key: str, use_reader=True) -> Optional[Dict]:
        """Get JSON value from cache"""
        try:
            value = self.get(key, use_reader)
            if value:
                return json.loads(value)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to decode JSON for key {key}: {e}")
        except Exception as e:
            logger.warning(f"Cache get_json failed for key {key}: {e}")
        return None
    
    def set_json(self, key: str, value: Dict, ttl: int = 900) -> bool:
        """Set JSON value in cache"""
        try:
            json_str = json.dumps(value)
            return self.set(key, json_str, ttl)
        except Exception as e:
            logger.warning(f"Cache set_json failed for key {key}: {e}")
        return False
    
    def ping(self) -> bool:
        """Test cache connectivity"""
        try:
            client = self.get_client(read_only=True)
            if client:
                return client.ping()
        except Exception as e:
            logger.warning(f"Cache ping failed: {e}")
        return False

class DAXCache:
    """DynamoDB Accelerator (DAX) cache client"""
    
    def __init__(self):
        self.ssm_client = boto3.client('ssm', region_name='eu-west-2')
        self._dax_client = None
        self._dynamodb_client = None
        
    def get_client(self):
        """Get DAX client with fallback to DynamoDB"""
        if self._dax_client is None:
            try:
                # Try to import DAX client
                import amazondax
                
                dax_endpoint = self._get_dax_endpoint()
                if dax_endpoint:
                    self._dax_client = amazondax.AmazonDaxClient.resource(
                        endpoint_url=f'dax://{dax_endpoint}',
                        region_name='eu-west-2'
                    )
                    logger.info("Connected to DAX cluster")
                else:
                    raise Exception("DAX endpoint not available")
                    
            except ImportError:
                logger.warning("DAX client not available, using DynamoDB directly")
                self._dax_client = boto3.resource('dynamodb', region_name='eu-west-2')
            except Exception as e:
                logger.warning(f"Could not connect to DAX: {e}, using DynamoDB directly")
                self._dax_client = boto3.resource('dynamodb', region_name='eu-west-2')
        
        return self._dax_client
    
    def _get_dax_endpoint(self):
        """Get DAX endpoint from SSM"""
        try:
            response = self.ssm_client.get_parameter(
                Name='/saas-platform/cache/dax/endpoint'
            )
            return response['Parameter']['Value']
        except Exception as e:
            logger.error(f"Failed to get DAX endpoint: {e}")
            return None
    
    def get_table(self, table_name: str):
        """Get DynamoDB table with DAX acceleration"""
        try:
            client = self.get_client()
            return client.Table(table_name)
        except Exception as e:
            logger.error(f"Failed to get table {table_name}: {e}")
            # Fallback to direct DynamoDB
            if self._dynamodb_client is None:
                self._dynamodb_client = boto3.resource('dynamodb', region_name='eu-west-2')
            return self._dynamodb_client.Table(table_name)

# Global cache instances
valkey_cache = ValkeyCache()
dax_cache = DAXCache()

def cache_key(prefix: str, *args) -> str:
    """Generate consistent cache key"""
    parts = [prefix] + [str(arg) for arg in args]
    return ':'.join(parts)

def tenant_cache_key(tenant_id: str, resource: str, *args) -> str:
    """Generate tenant-specific cache key"""
    return cache_key('tenant', tenant_id, resource, *args)

def user_cache_key(user_id: str, resource: str, *args) -> str:
    """Generate user-specific cache key"""
    return cache_key('user', user_id, resource, *args)

# Convenience functions
def get_cached_data(key: str, use_reader=True) -> Optional[Dict]:
    """Get cached JSON data"""
    return valkey_cache.get_json(key, use_reader)

def set_cached_data(key: str, data: Dict, ttl: int = 900) -> bool:
    """Set cached JSON data"""
    return valkey_cache.set_json(key, data, ttl)

def invalidate_cache(key: str) -> bool:
    """Invalidate cached data"""
    return valkey_cache.delete(key)

def get_dax_table(table_name: str):
    """Get DynamoDB table with DAX acceleration"""
    return dax_cache.get_table(table_name)

# Cache TTL constants
TTL_SHORT = 300      # 5 minutes
TTL_MEDIUM = 900     # 15 minutes
TTL_LONG = 3600      # 1 hour
TTL_VERY_LONG = 86400  # 24 hours