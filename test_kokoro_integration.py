#!/usr/bin/env python3
"""
Simple test script to verify Kokoro local TTS provider integration
"""

import asyncio
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.voicebot_app.services.tts.tts import TTSService


async def test_kokoro_provider():
    """Test the Kokoro local TTS provider integration"""
    
    # Create TTSService instance
    tts_service = TTSService()
    
    print(f"Current TTS provider: {tts_service.config.get_provider()}")
    print(f"Provider instance: {type(tts_service.provider).__name__}")
    
    # Test text generator
    async def test_text_generator():
        test_texts = [
            "Hello, this is a test of the Kokoro TTS provider.",
            "This should work with real-time streaming.",
            "Let's see if the integration is successful."
        ]
        for text in test_texts:
            yield text
            await asyncio.sleep(0.1)  # Small delay between chunks
    
    try:
        print("Starting TTS stream synthesis test...")
        
        # Count audio chunks received
        audio_chunk_count = 0
        
        async for audio_chunk in tts_service.stream_synthesis(test_text_generator()):
            audio_chunk_count += 1
            print(f"Received audio chunk {audio_chunk_count}: {len(audio_chunk)} bytes")
            
            # Stop after a few chunks for testing
            if audio_chunk_count >= 3:
                print("Test completed successfully!")
                break
        
        if audio_chunk_count == 0:
            print("No audio chunks received - this might be expected if Kokoro service is not running")
            print("Please ensure the Kokoro service is running in Docker")
        
    except Exception as e:
        print(f"Error during TTS test: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("Testing Kokoro Local TTS Provider Integration")
    print("=" * 50)
    
    asyncio.run(test_kokoro_provider())