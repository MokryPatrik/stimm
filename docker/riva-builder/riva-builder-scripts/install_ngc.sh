#!/bin/bash
# This script downloads and installs the NGC CLI.

# Set the version of the NGC CLI to install
NGC_CLI_VERSION="3.22.0"

# Create a temporary directory for the download
mkdir -p /tmp/ngc_cli && cd /tmp/ngc_cli

# Download the NGC CLI zip file
curl -fL "https://ngc.nvidia.com/downloads/ngc-cli_${NGC_CLI_VERSION}_linux.zip" -o ngc.zip

# Unzip the file
unzip ngc.zip

# Make the CLI executable
chmod +x ngc-cli/ngc

# Move the executable to a directory in the PATH
mv ngc-cli/ngc /usr/local/bin/ngc

# Clean up the temporary directory
cd / && rm -rf /tmp/ngc_cli