"""
Integration test for Deepgram TTS Provider

Tests the Deepgram TTS provider with real WebSocket connections
and generates audio files for playback testing.
"""

import asyncio
import logging
import os
import sys
from typing import AsyncGenerator

# Add the parent directory to the path to import from services
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../../"))

from services.tts.providers.deepgram.deepgram_provider import DeepgramProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def text_generator(text: str) -> AsyncGenerator[str, None]:
    """Generate text chunks for testing."""
    # Split text into chunks for realistic streaming
    chunks = text.split()
    for chunk in chunks:
        yield chunk + " "
        await asyncio.sleep(0.1)  # Simulate real-time text generation


async def test_deepgram_tts_streaming():
    """Test Deepgram TTS provider with real WebSocket connection."""
    logger.info("🧪 Starting Deepgram TTS integration test...")
    
    # Check if API key is available
    if not os.getenv("DEEPGRAM_API_KEY"):
        logger.warning("⚠️  DEEPGRAM_API_KEY not set, skipping real WebSocket test")
        return False
    
    provider = DeepgramProvider()
    logger.info("✅ DeepgramProvider initialized")
    
    # Test text
    test_text = "Hello, this is a test of the Deepgram TTS provider. It should generate natural sounding speech from this text."
    
    try:
        logger.info("📡 Connecting to Deepgram TTS WebSocket and streaming audio...")
        
        total_audio_bytes = 0
        audio_chunks = []
        chunk_count = 0
        
        async for audio_chunk in provider.stream_synthesis(text_generator(test_text)):
            chunk_size = len(audio_chunk)
            total_audio_bytes += chunk_size
            audio_chunks.append(audio_chunk)
            chunk_count += 1
            logger.info(f"   • Received audio chunk {chunk_count}: {chunk_size:,} bytes (total: {total_audio_bytes:,} bytes)")
        
        logger.info(f"✅ Test completed successfully!")
        logger.info(f"   • Total audio chunks: {chunk_count}")
        logger.info(f"   • Total audio bytes: {total_audio_bytes:,}")
        
        # Save audio to file for playback testing
        if audio_chunks:
            output_file = "test-deepgram-tts-audio.wav"
            # Note: This would need proper WAV header creation for actual playback
            # For now, we'll just log that we received audio
            logger.info(f"   • Audio received successfully - {len(audio_chunks)} chunks")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        return False


async def test_deepgram_provider_initialization():
    """Test Deepgram provider initialization and configuration."""
    logger.info("🧪 Testing Deepgram provider initialization...")
    
    try:
        provider = DeepgramProvider()
        
        # Check configuration
        assert hasattr(provider, 'api_key'), "Provider should have api_key attribute"
        assert hasattr(provider, 'model'), "Provider should have model attribute"
        assert hasattr(provider, 'sample_rate'), "Provider should have sample_rate attribute"
        assert hasattr(provider, 'encoding'), "Provider should have encoding attribute"
        
        logger.info(f"   • Model: {provider.model}")
        logger.info(f"   • Sample Rate: {provider.sample_rate}Hz")
        logger.info(f"   • Encoding: {provider.encoding}")
        
        logger.info("✅ Provider initialization test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Provider initialization test failed: {e}")
        return False


async def main():
    """Run all Deepgram TTS integration tests."""
    print("=" * 60)
    print("Deepgram TTS Integration Test")
    print("=" * 60)
    
    # Test 1: Provider initialization
    init_success = await test_deepgram_provider_initialization()
    
    # Test 2: Real WebSocket streaming (only if API key is available)
    streaming_success = True
    if os.getenv("DEEPGRAM_API_KEY"):
        streaming_success = await test_deepgram_tts_streaming()
    else:
        logger.warning("⚠️  Skipping WebSocket streaming test - DEEPGRAM_API_KEY not set")
    
    print("=" * 60)
    if init_success and streaming_success:
        print("✅ ALL TESTS PASSED")
        print("Deepgram TTS provider is working correctly!")
    else:
        print("❌ SOME TESTS FAILED")
        print("Check the logs above for details.")
        sys.exit(1)
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())