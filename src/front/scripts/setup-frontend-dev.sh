#!/bin/bash

# Frontend Development Setup Script
# This script sets up the frontend for dual-mode development

set -e

echo "🔧 Setting up Frontend Development Environment..."

# Check if we're in the correct directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: Please run this script from the src/front directory"
    exit 1
fi

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    npm install
fi

# Create .env.local file for frontend environment variables
cat > .env.local << EOF
# Frontend Environment Configuration
NEXT_PUBLIC_VOICEBOT_API_URL=http://localhost:8001
NEXT_PUBLIC_LIVEKIT_WS_URL=ws://localhost:7880
NEXT_PUBLIC_ENVIRONMENT_TYPE=local
EOF

echo "✅ Frontend development environment ready!"
echo ""
echo "🚀 Development Commands:"
echo "  npm run dev     - Start development server (http://localhost:3000)"
echo "  npm run build   - Build for production"
echo "  npm start       - Start production server"
echo ""
echo "🌐 Dual-Mode Support:"
echo "  - SSR (Server-Side Rendering): Uses container names in Docker dev"
echo "  - Client (Browser): Always uses localhost URLs"
echo ""