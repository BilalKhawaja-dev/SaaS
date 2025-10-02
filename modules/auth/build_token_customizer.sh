#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Script directory: $SCRIPT_DIR"

# Create a temporary directory for building the Lambda package
BUILD_DIR=$(mktemp -d)
echo "Building Lambda package in: $BUILD_DIR"

# Copy the token customizer code
cp "$SCRIPT_DIR/token_customizer.py" "$BUILD_DIR/"

# Create the zip file (no external dependencies needed)
cd "$BUILD_DIR"
zip -r token_customizer.zip . -x "*.git*" "*.DS_Store*"

# Move the zip file back to the module directory
mv token_customizer.zip "$SCRIPT_DIR/"

# Clean up
cd - > /dev/null
rm -rf "$BUILD_DIR"

echo "Token customizer Lambda package created: token_customizer.zip"