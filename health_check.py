#!/usr/bin/env python3
"""
Health check script for SaaS Platform
Validates that all services are running correctly
"""

import requests
import json
import sys
import os
from urllib.parse import urljoin

def check_service_health(service_url, service_name):
    """Check if a service is healthy"""
    try:
        response = requests.get(urljoin(service_url, '/health'), timeout=10)
        if response.status_code == 200:
            print(f"✅ {service_name}: Healthy")
            return True
        else:
            print(f"❌ {service_name}: Unhealthy (Status: {response.status_code})")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ {service_name}: Connection failed - {str(e)}")
        return False

def main():
    """Main health check function"""
    print("🏥 SaaS Platform Health Check")
    print("=" * 40)
    
    # Get API Gateway URL from terraform output
    try:
        import subprocess
        result = subprocess.run(['terraform', 'output', '-raw', 'api_gateway_url'], 
                              capture_output=True, text=True, cwd=os.path.dirname(__file__))
        if result.returncode == 0:
            api_gateway_url = result.stdout.strip()
            print(f"🌐 API Gateway URL: {api_gateway_url}")
        else:
            print("⚠️  Could not get API Gateway URL from terraform output")
            api_gateway_url = None
    except Exception as e:
        print(f"⚠️  Error getting terraform output: {e}")
        api_gateway_url = None
    
    all_healthy = True
    
    # Check API Gateway if available
    if api_gateway_url:
        if not check_service_health(api_gateway_url, "API Gateway"):
            all_healthy = False
    
    # Check individual services (if running locally)
    services = [
        ("http://localhost:5000", "Auth Service"),
        ("http://localhost:5001", "Support Service"), 
        ("http://localhost:5002", "Balance Service")
    ]
    
    for service_url, service_name in services:
        if not check_service_health(service_url, service_name):
            all_healthy = False
    
    print("=" * 40)
    if all_healthy:
        print("🎉 All services are healthy!")
        return 0
    else:
        print("💥 Some services are unhealthy!")
        return 1

if __name__ == "__main__":
    sys.exit(main())