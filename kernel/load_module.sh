#!/bin/bash
# SKMA-FON Kernel Module Loader
# Author: Soufian Carson

set -e

MODULE_NAME="monitoring_module"
PROC_PATH="/proc/optifiber/myinfo"

echo "SKMA-FON Kernel Module Loader"
echo "============================="

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root (use sudo)"
   exit 1
fi

# Function to load module
load_module() {
    echo "Building kernel module..."
    make clean && make
    
    echo "Loading kernel module..."
    insmod ${MODULE_NAME}.ko
    
    # Wait a moment for proc entry to be created
    sleep 1
    
    if [ -f "$PROC_PATH" ]; then
        echo "✓ Module loaded successfully"
        echo "✓ Proc entry created: $PROC_PATH"
        echo "✓ Testing proc interface:"
        head -10 "$PROC_PATH"
    else
        echo "✗ Module loaded but proc entry not found"
        exit 1
    fi
}

# Function to unload module
unload_module() {
    echo "Unloading kernel module..."
    if lsmod | grep -q "$MODULE_NAME"; then
        rmmod "$MODULE_NAME"
        echo "✓ Module unloaded successfully"
    else
        echo "Module not currently loaded"
    fi
}

# Function to check status
check_status() {
    echo "Checking module status..."
    if lsmod | grep -q "$MODULE_NAME"; then
        echo "✓ Module is loaded"
        if [ -f "$PROC_PATH" ]; then
            echo "✓ Proc entry exists: $PROC_PATH"
        else
            echo "✗ Proc entry missing"
        fi
    else
        echo "✗ Module not loaded"
    fi
}

# Main logic
case "$1" in
    load|start)
        load_module
        ;;
    unload|stop)
        unload_module
        ;;
    reload|restart)
        unload_module
        load_module
        ;;
    status)
        check_status
        ;;
    test)
        if [ -f "$PROC_PATH" ]; then
            echo "Testing proc interface:"
            cat "$PROC_PATH"
        else
            echo "Module not loaded or proc entry missing"
            exit 1
        fi
        ;;
    *)
        echo "Usage: $0 {load|unload|reload|status|test}"
        echo ""
        echo "Commands:"
        echo "  load     - Build and load the kernel module"
        echo "  unload   - Unload the kernel module"
        echo "  reload   - Unload and reload the module"
        echo "  status   - Check if module is loaded"
        echo "  test     - Display current monitoring data"
        exit 1
        ;;
esac

echo "Done."