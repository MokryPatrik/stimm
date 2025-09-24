#!/bin/bash
set -e

VOICEBOT_NETWORK="voicebot-network"

# Ensure the shared Docker network exists
if ! docker network inspect "$VOICEBOT_NETWORK" >/dev/null 2>&1; then
  docker network create "$VOICEBOT_NETWORK"
fi

# Ensure Docker config dir exists
mkdir -p /root/.docker

# Force-disable Windows credential store
echo '{}' > /root/.docker/config.json

echo "🔑 Logging in to nvcr.io with NGC API key..."
echo $NGC_API_KEY | docker login nvcr.io -u '$oauthtoken' --password-stdin
echo "✅ Docker login succeeded"


# Step 1: download the Riva quickstart bundle if not already there
if [ ! -f "./riva_quickstart_v2.19.0/riva_init.sh" ]; then
  echo "⬇️ Downloading Riva Quickstart 2.19.0..."
  ngc registry resource download-version "nvidia/riva/riva_quickstart:2.19.0" --org nvidia
fi

echo "📂 Current folder: $(pwd)"
ls -l ./riva_quickstart_v2.19.0

cd ./riva_quickstart_v2.19.0 || {
  echo "❌ Riva quickstart not found, something went wrong with download."
  exit 1
}

# Ensure scripts are executable
chmod +x riva_*.sh

# Step 2: init Riva (pulls images + models)
if [ ! -d "models" ]; then
  echo "⚙️ Initializing Riva..."
  ./riva_init.sh
fi

# Step 3: start Riva services
echo "🚀 Starting Riva services..."
./riva_start.sh

# Attach Riva to the shared network so the app can resolve riva-speech
if docker ps --format '{{.Names}}' | grep -q '^riva-speech$'; then
  docker network connect "$VOICEBOT_NETWORK" riva-speech >/dev/null 2>&1 || \
    echo "ℹ️ riva-speech already connected to $VOICEBOT_NETWORK"
fi

# Step 4: start your app (voicebot-app)
echo "▶️ Starting Riva services..."
