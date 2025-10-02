#!/usr/bin/env python3
"""
Comprehensive validation script for the SaaS Platform implementation
Tests all components for syntax errors, configuration issues, and completeness
"""

import os
import sys
import json
import subprocess
import re
from pathlib import Path
from typing import List, Dict, Tuple

class ValidationResult:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.passed = []
        
    def add_error(self, component: str, message: str):
        self.errors.append(f"❌ {component}: {message}")
        
    def add_warning(self, component: str, message: str):
        self.warnings.append(f"⚠️  {component}: {message}")
        
    def add_pass(self, component: str, message: str):
        self.passed.append(f"✅ {component}: {message}")

def validate_terraform_syntax() -> ValidationResult:
    """Validate Terraform configuration syntax"""
    result = ValidationResult()
    
    print("🔍 Validating Terraform Configuration...")
    
    # Check if terraform is available
    try:
        subprocess.run(['terraform', '--version'], capture_output=True, check=True)
        result.add_pass("Terraform", "CLI available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        result.add_error("Terraform", "CLI not found - install Terraform")
        return result
    
    # Initialize terraform
    try:
        subprocess.run(['terraform', 'init', '-backend=false'], 
                      capture_output=True, check=True, cwd='.')
        result.add_pass("Terraform", "Initialization successful")
    except subprocess.CalledProcessError as e:
        result.add_error("Terraform", f"Init failed: {e.stderr.decode()}")
        return result
    
    # Validate configuration
    try:
        proc = subprocess.run(['terraform', 'validate'], 
                            capture_output=True, check=True, cwd='.')
        result.add_pass("Terraform", "Configuration validation passed")
    except subprocess.CalledProcessError as e:
        result.add_error("Terraform", f"Validation failed: {e.stderr.decode()}")
    
    return result

def validate_python_syntax() -> ValidationResult:
    """Validate Python files for syntax errors"""
    result = ValidationResult()
    
    print("🐍 Validating Python Files...")
    
    python_files = [
        'docker/subscription-service/app.py',
        'docker/support-service/app.py',
        'shared/jwt_utils.py',
        'shared/cache_utils.py',
        'modules/api/authorizer.py',
        'modules/auth/token_customizer.py',
        'modules/notifications/ticket_router.py',
        'migrations/run_migrations.py',
        'test_notifications.py'
    ]
    
    for file_path in python_files:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    compile(f.read(), file_path, 'exec')
                result.add_pass("Python", f"{file_path} syntax valid")
            except SyntaxError as e:
                result.add_error("Python", f"{file_path} syntax error: {e}")
            except Exception as e:
                result.add_warning("Python", f"{file_path} compile warning: {e}")
        else:
            result.add_warning("Python", f"{file_path} not found")
    
    return result

def validate_docker_files() -> ValidationResult:
    """Validate Dockerfile syntax"""
    result = ValidationResult()
    
    print("🐳 Validating Docker Files...")
    
    dockerfiles = [
        'docker/frontend/Dockerfile',
        'docker/subscription-service/Dockerfile',
        'docker/support-service/Dockerfile'
    ]
    
    for dockerfile in dockerfiles:
        if os.path.exists(dockerfile):
            try:
                with open(dockerfile, 'r') as f:
                    content = f.read()
                    
                # Basic Dockerfile validation
                if not content.strip().startswith('FROM'):
                    result.add_error("Docker", f"{dockerfile} must start with FROM")
                elif 'EXPOSE' not in content:
                    result.add_warning("Docker", f"{dockerfile} missing EXPOSE directive")
                else:
                    result.add_pass("Docker", f"{dockerfile} syntax looks valid")
                    
            except Exception as e:
                result.add_error("Docker", f"{dockerfile} read error: {e}")
        else:
            result.add_error("Docker", f"{dockerfile} not found")
    
    return result

def validate_json_files() -> ValidationResult:
    """Validate JSON configuration files"""
    result = ValidationResult()
    
    print("📄 Validating JSON Files...")
    
    # Check for any JSON files
    json_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.json'):
                json_files.append(os.path.join(root, file))
    
    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                json.load(f)
            result.add_pass("JSON", f"{json_file} valid")
        except json.JSONDecodeError as e:
            result.add_error("JSON", f"{json_file} invalid: {e}")
        except Exception as e:
            result.add_warning("JSON", f"{json_file} read error: {e}")
    
    if not json_files:
        result.add_pass("JSON", "No JSON files found to validate")
    
    return result

def validate_shell_scripts() -> ValidationResult:
    """Validate shell scripts"""
    result = ValidationResult()
    
    print("🔧 Validating Shell Scripts...")
    
    shell_scripts = [
        'deploy.sh',
        'modules/api/build_authorizer.sh',
        'modules/auth/build_token_customizer.sh'
    ]
    
    for script in shell_scripts:
        if os.path.exists(script):
            try:
                with open(script, 'r') as f:
                    content = f.read()
                    
                # Basic shell script validation
                if content.startswith('#!/bin/bash') or content.startswith('#!/bin/sh'):
                    result.add_pass("Shell", f"{script} has proper shebang")
                else:
                    result.add_warning("Shell", f"{script} missing shebang")
                    
                # Check for common issues
                if 'set -e' not in content:
                    result.add_warning("Shell", f"{script} consider adding 'set -e' for error handling")
                    
            except Exception as e:
                result.add_error("Shell", f"{script} read error: {e}")
        else:
            result.add_warning("Shell", f"{script} not found")
    
    return result

def validate_module_structure() -> ValidationResult:
    """Validate Terraform module structure"""
    result = ValidationResult()
    
    print("📁 Validating Module Structure...")
    
    required_modules = [
        'networking', 'compute', 'database', 'auth', 'api', 
        'cache', 'security', 'monitoring', 'notifications'
    ]
    
    for module in required_modules:
        module_path = f"modules/{module}"
        if os.path.exists(module_path):
            # Check for required files
            main_tf = f"{module_path}/main.tf"
            variables_tf = f"{module_path}/variables.tf"
            outputs_tf = f"{module_path}/outputs.tf"
            
            if os.path.exists(main_tf):
                result.add_pass("Module", f"{module} has main.tf")
            else:
                result.add_error("Module", f"{module} missing main.tf")
                
            if os.path.exists(variables_tf):
                result.add_pass("Module", f"{module} has variables.tf")
            else:
                result.add_warning("Module", f"{module} missing variables.tf")
                
            if os.path.exists(outputs_tf):
                result.add_pass("Module", f"{module} has outputs.tf")
            else:
                result.add_warning("Module", f"{module} missing outputs.tf")
        else:
            result.add_error("Module", f"{module} directory not found")
    
    return result

def validate_dependencies() -> ValidationResult:
    """Validate that all dependencies are properly referenced"""
    result = ValidationResult()
    
    print("🔗 Validating Dependencies...")
    
    # Check main.tf for module dependencies
    if os.path.exists('main.tf'):
        try:
            with open('main.tf', 'r') as f:
                content = f.read()
                
            # Check for module blocks
            modules_found = re.findall(r'module\s+"([^"]+)"', content)
            expected_modules = ['networking', 'security', 'database', 'cache', 'auth', 'api', 'compute', 'monitoring', 'notifications']
            
            for module in expected_modules:
                if module in modules_found:
                    result.add_pass("Dependencies", f"Module {module} referenced in main.tf")
                else:
                    result.add_error("Dependencies", f"Module {module} not found in main.tf")
                    
        except Exception as e:
            result.add_error("Dependencies", f"Error reading main.tf: {e}")
    else:
        result.add_error("Dependencies", "main.tf not found")
    
    return result

def validate_shared_utilities() -> ValidationResult:
    """Validate shared utility files"""
    result = ValidationResult()
    
    print("🛠️  Validating Shared Utilities...")
    
    shared_files = {
        'shared/jwt_utils.py': ['token_required', 'get_current_user'],
        'shared/cache_utils.py': ['get_valkey_client', 'tenant_cache_key']
    }
    
    for file_path, required_functions in shared_files.items():
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    
                for func in required_functions:
                    if f"def {func}" in content:
                        result.add_pass("Shared", f"{file_path} has {func}")
                    else:
                        result.add_error("Shared", f"{file_path} missing {func}")
                        
            except Exception as e:
                result.add_error("Shared", f"Error reading {file_path}: {e}")
        else:
            result.add_error("Shared", f"{file_path} not found")
    
    return result

def validate_task_completion() -> ValidationResult:
    """Validate that all tasks are marked as completed"""
    result = ValidationResult()
    
    print("📋 Validating Task Completion...")
    
    tasks_file = '.kiro/specs/saas-platform-fixes/tasks.md'
    if os.path.exists(tasks_file):
        try:
            with open(tasks_file, 'r') as f:
                content = f.read()
                
            # Count completed vs total tasks
            completed_tasks = content.count('- [x]')
            incomplete_tasks = content.count('- [ ]')
            total_tasks = completed_tasks + incomplete_tasks
            
            if incomplete_tasks == 0:
                result.add_pass("Tasks", f"All {total_tasks} tasks completed")
            else:
                result.add_error("Tasks", f"{incomplete_tasks} of {total_tasks} tasks incomplete")
                
        except Exception as e:
            result.add_error("Tasks", f"Error reading tasks file: {e}")
    else:
        result.add_warning("Tasks", "Tasks file not found")
    
    return result

def validate_configuration_consistency() -> ValidationResult:
    """Validate configuration consistency across files"""
    result = ValidationResult()
    
    print("⚙️  Validating Configuration Consistency...")
    
    # Check that service ports are consistent
    port_mappings = {
        'subscription-service': 5000,
        'support-service': 5001,
        'frontend': 5002
    }
    
    for service, expected_port in port_mappings.items():
        # Check Docker files
        dockerfile = f"docker/{service}/Dockerfile"
        if os.path.exists(dockerfile):
            with open(dockerfile, 'r') as f:
                content = f.read()
                if f"EXPOSE {expected_port}" in content:
                    result.add_pass("Config", f"{service} Dockerfile has correct port {expected_port}")
                else:
                    result.add_warning("Config", f"{service} Dockerfile port mismatch")
    
    # Check that all services use shared utilities
    service_files = [
        'docker/subscription-service/app.py',
        'docker/support-service/app.py'
    ]
    
    for service_file in service_files:
        if os.path.exists(service_file):
            with open(service_file, 'r') as f:
                content = f.read()
                if 'from jwt_utils import' in content and 'from cache_utils import' in content:
                    result.add_pass("Config", f"{service_file} uses shared utilities")
                else:
                    result.add_error("Config", f"{service_file} not using shared utilities")
    
    return result

def main():
    """Run all validations"""
    print("🚀 SaaS Platform Implementation Validation")
    print("=" * 60)
    
    all_results = []
    
    # Run all validation functions
    validations = [
        validate_terraform_syntax,
        validate_python_syntax,
        validate_docker_files,
        validate_json_files,
        validate_shell_scripts,
        validate_module_structure,
        validate_dependencies,
        validate_shared_utilities,
        validate_task_completion,
        validate_configuration_consistency
    ]
    
    for validation_func in validations:
        try:
            result = validation_func()
            all_results.append(result)
        except Exception as e:
            error_result = ValidationResult()
            error_result.add_error("Validation", f"{validation_func.__name__} failed: {e}")
            all_results.append(error_result)
    
    # Compile results
    total_errors = sum(len(r.errors) for r in all_results)
    total_warnings = sum(len(r.warnings) for r in all_results)
    total_passed = sum(len(r.passed) for r in all_results)
    
    print("\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)
    
    # Print all results
    for result in all_results:
        for msg in result.passed:
            print(msg)
        for msg in result.warnings:
            print(msg)
        for msg in result.errors:
            print(msg)
    
    print("\n" + "=" * 60)
    print(f"📈 FINAL RESULTS:")
    print(f"✅ Passed: {total_passed}")
    print(f"⚠️  Warnings: {total_warnings}")
    print(f"❌ Errors: {total_errors}")
    
    if total_errors == 0:
        print("\n🎉 VALIDATION SUCCESSFUL! Implementation is ready for deployment.")
        return 0
    else:
        print(f"\n💥 VALIDATION FAILED! Please fix {total_errors} errors before deployment.")
        return 1

if __name__ == "__main__":
    sys.exit(main())