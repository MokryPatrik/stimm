#!/usr/bin/env python3
"""
Detailed Hume WebSocket authentication debug script
Tests different authentication methods and API key formats
"""

import asyncio
import websockets
import json
import os
from urllib.parse import urlencode

async def test_websocket_connection(url, headers=None):
    """Test WebSocket connection with given URL and headers"""
    print(f"🔗 Testing connection to: {url}")
    if headers:
        print(f"📋 Headers: {headers}")
    
    try:
        async with websockets.connect(url, extra_headers=headers) as websocket:
            print("✅ WebSocket connection established successfully!")
            
            # Send a test message
            test_message = {
                "text": "Bonjour, ceci est un test.",
                "voice": {
                    "name": "5b612d83-696a-4089-88a7-da3e8e8126e7"
                },
                "config": {
                    "audio_encoding": "LINEAR16",
                    "sample_rate": 24000
                }
            }
            
            await websocket.send(json.dumps(test_message))
            print("📤 Test message sent")
            
            # Wait for response
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print(f"📥 Received response: {response}")
            
            return True
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

async def main():
    print("🧪 Hume WebSocket Authentication Detailed Debug")
    print("=" * 50)
    
    api_key = os.getenv("HUME_API_KEY", "")
    print(f"🔑 API Key: {api_key[:10]}...{api_key[-10:] if len(api_key) > 20 else ''}")
    print(f"📏 Key length: {len(api_key)}")
    
    # Test different authentication methods
    
    # Method 1: Query parameter (current implementation)
    print("\n1️⃣ Testing Query Parameter Authentication")
    base_url = "wss://api.hume.ai/v0/tts/stream/input"
    params = {
        "api_key": api_key,
        "instant_mode": "true",
        "strip_headers": "true",
        "no_binary": "true"
    }
    url_with_query = f"{base_url}?{urlencode(params)}"
    await test_websocket_connection(url_with_query)
    
    # Method 2: Headers authentication
    print("\n2️⃣ Testing Headers Authentication")
    headers = {
        "X-API-Key": api_key
    }
    await test_websocket_connection(base_url, headers)
    
    # Method 3: Authorization header
    print("\n3️⃣ Testing Authorization Header")
    headers_auth = {
        "Authorization": f"Bearer {api_key}"
    }
    await test_websocket_connection(base_url, headers_auth)
    
    # Method 4: No authentication (should fail)
    print("\n4️⃣ Testing No Authentication (should fail)")
    await test_websocket_connection(base_url)
    
    print("\n" + "=" * 50)
    print("🧪 Debug complete")

if __name__ == "__main__":
    asyncio.run(main())