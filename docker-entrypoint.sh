#!/bin/bash
set -e

# Create all necessary directories
mkdir -p /app/data

# Print environment for debugging
echo "==== Environment ===="
echo "Current directory: $(pwd)"
echo "DATA_DIR from env: $DATA_DIR"

# Make the script executable
chmod +x /app/main.py

# Execute the main application with all arguments passed to this script
echo "==== Starting application ===="
exec python /app/main.py "$@"