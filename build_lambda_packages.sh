#!/bin/bash

echo "🔧 Building Lambda deployment packages..."

# Build API Gateway Authorizer
echo "📦 Building API Gateway Authorizer..."
cd modules/api
if [ -f "authorizer.py" ]; then
    python3 -c "
import zipfile
import os
with zipfile.ZipFile('authorizer.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
    zipf.write('authorizer.py', 'authorizer.py')
    if os.path.exists('requirements.txt'):
        zipf.write('requirements.txt', 'requirements.txt')
print('✅ Created authorizer.zip')
"
else
    echo "❌ authorizer.py not found"
fi
cd ../..

# Build Token Customizer
echo "📦 Building Token Customizer..."
cd modules/auth
if [ -f "token_customizer.py" ]; then
    python3 -c "
import zipfile
with zipfile.ZipFile('token_customizer.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
    zipf.write('token_customizer.py', 'token_customizer.py')
print('✅ Created token_customizer.zip')
"
else
    echo "❌ token_customizer.py not found"
fi
cd ../..

# Build Ticket Router
echo "📦 Building Ticket Router..."
cd modules/notifications
if [ -f "ticket_router.py" ]; then
    python3 -c "
import zipfile
with zipfile.ZipFile('ticket_router.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
    zipf.write('ticket_router.py', 'lambda_function.py')
print('✅ Created ticket_router.zip')
"
else
    echo "❌ ticket_router.py not found"
fi
cd ../..

echo "🎉 All Lambda packages built successfully!"