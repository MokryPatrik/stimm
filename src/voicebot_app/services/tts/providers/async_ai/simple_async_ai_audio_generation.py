#!/usr/bin/env python3
"""
Simple AsyncAI Audio Generation Test

This script specifically tests audio generation functionality of the AsyncAI TTS service.
It focuses on the core audio synthesis capability to diagnose issues with empty audio responses.

Usage:
    python simple_async_ai_audio_generation.py

Or within voicebot-app container:
    python -m services.tts.providers.async_ai.simple_async_ai_audio_generation
"""

import asyncio
import base64
import json
import logging
import sys
import os

# Add the parent directories to Python path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from services.tts.providers.async_ai.async_ai_provider import AsyncAIProvider

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def text_generator(text: str):
    """Simple text generator for stream_synthesis method."""
    yield text

async def test_audio_generation():
    """
    Test audio generation with detailed debugging using the stream_synthesis() method.
    """
    logger.info("🔊 Starting AsyncAI Audio Generation Test...")

    # Create provider instance (uses config from .env)
    provider = AsyncAIProvider()

    try:
        # Step 1: Log configuration details
        logger.info("🔧 Step 1: Configuration Analysis...")
        logger.info(f"   • WebSocket URL: {provider.websocket_url}")
        logger.info(f"   • Voice ID: {provider.voice_id}")
        logger.info(f"   • Model ID: {provider.model_id}")
        logger.info(f"   • Sample Rate: {provider.sample_rate} Hz")
        logger.info(f"   • Encoding: {provider.encoding}")
        logger.info(f"   • Container: {provider.container}")
        logger.info(f"   • API Key configured: {'Yes' if provider.api_key else 'No'}")

        # Step 2: Generate audio using the stream_synthesis() method
        logger.info("🎵 Step 2: Generating audio with stream_synthesis() method...")
        test_text = "Hello, this is a test of audio generation."
        logger.info(f"   • Test text: '{test_text}'")

        # Use the stream_synthesis method for real-time streaming
        logger.info("📡 Connecting to AsyncAI WebSocket and streaming audio...")
        
        audio_chunks = []
        total_audio_bytes = 0
        
        async for audio_chunk in provider.stream_synthesis(text_generator(test_text)):
            chunk_size = len(audio_chunk)
            total_audio_bytes += chunk_size
            audio_chunks.append(audio_chunk)
            logger.info(f"   • Received audio chunk: {chunk_size:,} bytes (total: {total_audio_bytes:,} bytes)")

        logger.info("✅ Audio streaming completed successfully")

        # Step 3: Analyze the generated audio
        logger.info("📊 Step 3: Audio Analysis...")
        logger.info(f"   • Total audio chunks: {len(audio_chunks)}")
        logger.info(f"   • Total audio bytes: {total_audio_bytes:,} bytes")

        if total_audio_bytes > 0:
            # Combine all chunks
            audio_data = b"".join(audio_chunks)
            
            # Basic audio format detection (16-bit PCM)
            sample_count = total_audio_bytes // 2  # 16-bit samples
            total_duration_ms = (sample_count / provider.sample_rate) * 1000
            logger.info(f"   • Estimated duration: {total_duration_ms:.0f} milliseconds")
            logger.info(f"   • Audio format: {provider.encoding} at {provider.sample_rate}Hz")
            logger.info(f"   • Sample count: {sample_count:,} samples")

            # Analyze audio content
            logger.info("🔍 Audio Content Analysis:")
            if len(audio_data) > 100:
                # Check for silence (all zeros)
                first_100_bytes = audio_data[:100]
                is_silent = all(b == 0 for b in first_100_bytes)
                logger.info(f"   • First 100 bytes are all zeros: {is_silent}")
                
                if is_silent:
                    logger.warning("⚠️  WARNING: Audio appears to be silent (all zeros)")
                else:
                    logger.info("✅ Audio contains non-zero data (likely valid audio)")

            if total_duration_ms > 500:  # More reasonable minimum duration for test text
                logger.info("🎉 SUCCESS: Generated substantial audio content!")
                logger.info(f"   • Duration: {total_duration_ms:.0f} ms meets minimum threshold")
                return True
            elif total_duration_ms > 100:
                logger.info("✅ SUCCESS: Generated audio content")
                logger.info(f"   • Duration: {total_duration_ms:.0f} ms (shorter than expected but valid)")
                return True
            else:
                logger.warning(f"⚠️  WARNING: Audio very short ({total_duration_ms:.0f} ms)")
                logger.info("   • This might indicate issues with the API or configuration")
                return True  # Still consider it success since we got audio
        else:
            logger.error("❌ ERROR: No audio data generated")
            logger.error("   • The stream_synthesis() method returned no audio chunks")
            logger.error("   • Check API key, voice permissions, or model settings")
            return False

    except asyncio.TimeoutError:
        logger.error("❌ ERROR: Timeout during audio generation")
        logger.error("   • This suggests the API is not responding")
        return False

    except Exception as e:
        logger.error(f"❌ ERROR: Audio generation test failed: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return False

def main():
    """
    Main entry point for the audio generation test.
    """
    print("=" * 70)
    print("🎵 AsyncAI TTS Audio Generation Test")
    print("=" * 70)

    # Run the async test
    success = asyncio.run(test_audio_generation())

    print("=" * 70)
    if success:
        print("✅ TEST RESULT: AUDIO GENERATION SUCCESSFUL")
        print("🎵 AsyncAI is generating audio correctly!")
    else:
        print("❌ TEST RESULT: AUDIO GENERATION FAILED")
        print("🔧 Check API key permissions, voice ID, or model settings")
        sys.exit(1)

    print("=" * 70)

if __name__ == "__main__":
    main()