#!/usr/bin/env python3
"""
Minimalistic AsyncAI WebSocket Connection Test

This script tests the basic WebSocket connection to AsyncAI TTS service
without performing any synthesis. It verifies that:
1. The connection can be established
2. The initialization message can be sent
3. The connection can be properly closed

Usage:
    python simple_async_ai_connect_test.py

Or within voicebot-app container:
    python -m services.tts.providers.async_ai.simple_async_ai_connect_test
"""

import asyncio
import logging
import sys
import os

# Add the parent directories to Python path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from services.tts.providers.async_ai.async_ai_provider import AsyncAIProvider

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_async_ai_connection():
    """
    Test basic WebSocket connection to AsyncAI TTS service.
    """
    logger.info("Starting AsyncAI WebSocket connection test...")

    # Create provider instance (uses config from .env)
    provider = AsyncAIProvider()

    try:
        # Test 1: Establish connection
        logger.info("Testing WebSocket connection...")
        await provider.connect()
        logger.info("✓ WebSocket connection established successfully")

        # Test 2: Verify connection is active
        if provider.connected and provider.websocket:
            logger.info("✓ Provider reports connected state")
        else:
            raise Exception("Provider connection state invalid")

        # Test 3: Test disconnect
        logger.info("Testing WebSocket disconnection...")
        await provider.disconnect()
        logger.info("✓ WebSocket disconnection successful")

        # Final verification
        if not provider.connected:
            logger.info("✓ Provider reports disconnected state")
        else:
            raise Exception("Provider still reports connected state after disconnect")

        logger.info("🎉 All connection tests passed!")
        return True

    except Exception as e:
        logger.error(f"❌ Connection test failed: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return False

    finally:
        # Ensure cleanup happens
        if provider.connected:
            try:
                await provider.disconnect()
                logger.info("Cleanup: Disconnected provider")
            except Exception as e:
                logger.warning(f"Cleanup: Error during disconnect: {e}")

def main():
    """
    Main entry point for the connection test.
    """
    print("=" * 60)
    print("AsyncAI TTS WebSocket Connection Test")
    print("=" * 60)

    # Run the async test
    success = asyncio.run(test_async_ai_connection())

    print("=" * 60)
    if success:
        print("✅ TEST RESULT: PASSED")
        print("The AsyncAI WebSocket connection is working correctly.")
    else:
        print("❌ TEST RESULT: FAILED")
        print("Check the logs above for details.")
        sys.exit(1)

    print("=" * 60)

if __name__ == "__main__":
    main()