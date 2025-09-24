"""Debug test for Hume SDK TTS provider."""

import asyncio
import os
import sys
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from voicebot.tts.hume_provider import create_hume_provider
from voicebot.tts.models import SynthesisConfig, SynthesisChunk


async def test_hume_sdk_provider_debug():
    """Debug test for Hume SDK TTS provider."""
    api_key = os.getenv('HUME_API_KEY')
    if not api_key:
        print('❌ HUME_API_KEY not found in environment')
        return False
    
    print('✅ HUME_API_KEY found')
    
    try:
        provider = create_hume_provider(api_key=api_key)
        print(f'✅ Provider created: {provider.name}')
        
        # Test configuration
        config = SynthesisConfig(
            voice_name='Salli',
            language_code='en-US',
            sample_rate_hz=22050
        )
        
        # Test text stream
        async def text_stream():
            print('📝 Creating text stream...')
            yield SynthesisChunk(text='Hello, this is a test.', is_final=True)
            print('📝 Text stream completed')
        
        # Test streaming
        print('🔄 Starting streaming test...')
        audio_chunks = []
        
        # Get the generator
        stream_generator = provider.stream(config, text_stream())
        print('✅ Stream generator created')
        
        try:
            async for audio_chunk in stream_generator:
                print(f'🎵 Received audio chunk: sequence={audio_chunk.sequence}, size={len(audio_chunk.data)}, is_last={audio_chunk.is_last}')
                audio_chunks.append(audio_chunk)
        except Exception as stream_error:
            print(f'❌ Error during streaming: {stream_error}')
            import traceback
            traceback.print_exc()
            return False
        
        print(f'📊 Streaming completed: {len(audio_chunks)} audio chunks received')
        
        if audio_chunks:
            total_audio_size = sum(len(chunk.data) for chunk in audio_chunks)
            print(f'✅ Total audio data: {total_audio_size} bytes')
            return True
        else:
            print('❌ No audio chunks received')
            return False
            
    except Exception as e:
        print(f'❌ Error during test: {e}')
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function."""
    print("🧪 Debug Testing Hume SDK TTS Provider")
    print("=" * 50)
    
    success = await test_hume_sdk_provider_debug()
    
    print("=" * 50)
    if success:
        print("✅ Debug test passed!")
        sys.exit(0)
    else:
        print("❌ Debug test failed!")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())