#!/usr/bin/env python3
"""
Quick syntax and structure check for the SaaS Platform
"""

import os
import ast
import json

def check_python_files():
    """Check Python files for syntax errors"""
    print("🐍 Checking Python Files...")
    
    python_files = [
        'docker/subscription-service/app.py',
        'docker/support-service/app.py',
        'shared/jwt_utils.py',
        'shared/cache_utils.py',
        'modules/api/authorizer.py',
        'modules/auth/token_customizer.py',
        'modules/notifications/ticket_router.py',
        'migrations/run_migrations.py',
        'test_notifications.py',
        'validate_implementation.py'
    ]
    
    errors = 0
    for file_path in python_files:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                ast.parse(content)
                print(f"✅ {file_path}")
            except SyntaxError as e:
                print(f"❌ {file_path}: {e}")
                errors += 1
            except Exception as e:
                print(f"⚠️  {file_path}: {e}")
        else:
            print(f"⚠️  {file_path}: File not found")
    
    return errors

def check_required_files():
    """Check that all required files exist"""
    print("\n📁 Checking Required Files...")
    
    required_files = [
        'main.tf',
        'variables.tf',
        'deploy.sh',
        'README.md',
        '.kiro/specs/saas-platform-fixes/tasks.md',
        'shared/jwt_utils.py',
        'shared/cache_utils.py'
    ]
    
    missing = 0
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}: Missing")
            missing += 1
    
    return missing

def check_module_structure():
    """Check Terraform module structure"""
    print("\n🏗️  Checking Module Structure...")
    
    modules = [
        'networking', 'compute', 'database', 'auth', 'api',
        'cache', 'security', 'monitoring', 'notifications'
    ]
    
    errors = 0
    for module in modules:
        module_path = f"modules/{module}"
        if os.path.exists(module_path):
            main_tf = f"{module_path}/main.tf"
            if os.path.exists(main_tf):
                print(f"✅ {module}")
            else:
                print(f"❌ {module}: Missing main.tf")
                errors += 1
        else:
            print(f"❌ {module}: Directory missing")
            errors += 1
    
    return errors

def check_tasks_completion():
    """Check if all tasks are completed"""
    print("\n📋 Checking Task Completion...")
    
    tasks_file = '.kiro/specs/saas-platform-fixes/tasks.md'
    if os.path.exists(tasks_file):
        with open(tasks_file, 'r') as f:
            content = f.read()
        
        completed = content.count('- [x]')
        incomplete = content.count('- [ ]')
        
        if incomplete == 0:
            print(f"✅ All {completed} tasks completed")
            return 0
        else:
            print(f"❌ {incomplete} tasks still incomplete")
            return incomplete
    else:
        print("❌ Tasks file not found")
        return 1

def main():
    print("🔍 Quick Implementation Check")
    print("=" * 40)
    
    total_errors = 0
    
    total_errors += check_python_files()
    total_errors += check_required_files()
    total_errors += check_module_structure()
    total_errors += check_tasks_completion()
    
    print("\n" + "=" * 40)
    if total_errors == 0:
        print("🎉 All checks passed! Implementation looks good.")
    else:
        print(f"💥 Found {total_errors} issues that need attention.")
    
    return total_errors

if __name__ == "__main__":
    exit(main())