#!/bin/bash
# Docker entrypoint script for SKMA-FON agent

set -e

echo "Starting SKMA-FON Agent..."
echo "Agent Name: ${AGENT_NAME:-skma-fon-agent}"
echo "Cloud API URL: ${CLOUD_API_URL:-http://localhost:5000}"
echo "Log Level: ${LOG_LEVEL:-INFO}"

# Check if running in privileged mode (needed for kernel module)
if [ -w /proc/sys ]; then
    echo "Running in privileged mode - attempting to load kernel module..."
    
    # Try to load the kernel module
    if [ -f "./kernel/monitoring_module.ko" ]; then
        echo "Loading monitoring kernel module..."
        insmod ./kernel/monitoring_module.ko || echo "Warning: Could not load kernel module (may already be loaded or not supported)"
        
        # Verify module is loaded
        if lsmod | grep -q monitoring_module; then
            echo "✓ Kernel module loaded successfully"
        else
            echo "⚠ Kernel module not loaded - running in simulation mode"
        fi
    else
        echo "⚠ Kernel module not found - running in simulation mode"
    fi
else
    echo "⚠ Not running in privileged mode - running in simulation mode"
fi

# Wait for cloud API to be available
echo "Waiting for cloud API at ${CLOUD_API_URL}..."
for i in {1..30}; do
    if curl -s "${CLOUD_API_URL}/api/health" > /dev/null 2>&1; then
        echo "✓ Cloud API is available"
        break
    fi
    echo "Attempt $i/30: Waiting for cloud API..."
    sleep 2
done

# Create necessary directories
mkdir -p /tmp/skma-fon

echo "Starting monitoring agent..."
exec "$@"