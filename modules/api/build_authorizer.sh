#!/bin/bash

set -euo pipefail

# Error handling
handle_error() {
    echo "Error occurred at line $1"
    [ -n "${BUILD_DIR:-}" ] && rm -rf "$BUILD_DIR"
    exit 1
}

trap 'handle_error $LINENO' ERR

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Script directory: $SCRIPT_DIR"

# Create a temporary directory for building the Lambda package
BUILD_DIR=$(mktemp -d)
echo "Building Lambda package in: $BUILD_DIR"

# Copy the authorizer code
cp "$SCRIPT_DIR/authorizer.py" "$BUILD_DIR/" || { echo "Failed to copy authorizer.py"; exit 1; }
cp "$SCRIPT_DIR/requirements.txt" "$BUILD_DIR/" || { echo "Failed to copy requirements.txt"; exit 1; }

# Install dependencies
cd "$BUILD_DIR"
pip install -r requirements.txt -t . || { echo "Failed to install dependencies"; exit 1; }

# Remove unnecessary files to reduce package size
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete
find . -name "*.pyo" -delete
find . -name "*.dist-info" -type d -exec rm -rf {} + 2>/dev/null || true

# Create the zip file
zip -r authorizer.zip . -x "*.git*" "*.DS_Store*" "requirements.txt"

# Move the zip file back to the module directory
mv authorizer.zip "$SCRIPT_DIR/"

# Clean up
cd - > /dev/null
rm -rf "$BUILD_DIR"

echo "Lambda package created: authorizer.zip"