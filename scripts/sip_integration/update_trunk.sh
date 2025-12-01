#!/bin/bash
# Update SIP trunk configuration
# Wrapper script for update_trunk.py

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="${SCRIPT_DIR}/update_trunk.py"

if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Error: $PYTHON_SCRIPT not found."
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found."
    exit 1
fi

# Pass all arguments to the Python script
exec python3 "$PYTHON_SCRIPT" "$@"