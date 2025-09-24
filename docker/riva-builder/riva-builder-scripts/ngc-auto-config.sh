#!/bin/bash
set -e

# Load secrets from .env into environment
if [ -f "./.env" ]; then
  export $(grep -v '^#' ./.env | xargs)
fi

# Run the expect script
/app/riva-builder-scripts/ngc-auto-config.exp
