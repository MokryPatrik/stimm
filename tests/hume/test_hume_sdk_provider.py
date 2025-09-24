"""Test script for Hume SDK TTS provider."""

import asyncio
import os
import sys
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from voicebot.tts.hume_provider import create_hume_provider
from voicebot.tts.models import SynthesisConfig, SynthesisChunk


async def test_hume_sdk_provider():
    """Test the Hume SDK TTS provider."""
    api_key = os.getenv('HUME_API_KEY')
    if not api_key:
        print('❌ HUME_API_KEY not found in environment')
        return False
    
    print('✅ HUME_API_KEY found')
    
    try:
        provider = create_hume_provider(api_key=api_key)
        print(f'✅ Provider created: {provider.name}')
        print(f'✅ Capabilities: {provider.capabilities}')
        
        # Test configuration
        config = SynthesisConfig(
            voice_name='Salli',
            language_code='en-US',
            sample_rate_hz=22050
        )
        
        # Test text stream
        async def text_stream():
            print('📝 Sending text chunk...')
            yield SynthesisChunk(text='Hello, this is a test of the Hume SDK provider.', is_final=True)
        
        # Test streaming
        print('🔄 Testing streaming...')
        audio_chunks = []
        try:
            async for audio_chunk in provider.stream(config, text_stream()):
                print(f'🎵 Received audio chunk: sequence={audio_chunk.sequence}, size={len(audio_chunk.data)}, is_last={audio_chunk.is_last}')
                audio_chunks.append(audio_chunk)
        except Exception as stream_error:
            print(f'❌ Error during streaming: {stream_error}')
            import traceback
            traceback.print_exc()
            return False
        
        if audio_chunks:
            print(f'✅ Successfully received {len(audio_chunks)} audio chunks')
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
    print("🧪 Testing Hume SDK TTS Provider")
    print("=" * 50)
    
    success = await test_hume_sdk_provider()
    
    print("=" * 50)
    if success:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Tests failed!")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())