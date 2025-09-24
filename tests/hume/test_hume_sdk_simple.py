"""Simple test to verify Hume SDK works directly."""

import os
import sys
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from hume import HumeClient
from hume.tts import AudioEncoding, FormatWav, PostedUtterance, PostedUtteranceVoiceWithName


def test_hume_sdk_direct():
    """Test Hume SDK directly without our provider wrapper."""
    api_key = os.getenv('HUME_API_KEY')
    if not api_key:
        print('❌ HUME_API_KEY not found in environment')
        return False
    
    print('✅ HUME_API_KEY found')
    
    try:
        # Create Hume client
        client = HumeClient(api_key=api_key)
        tts_client = client.tts
        
        print('✅ Hume client created')
        
        # Create utterance
        utterance = PostedUtterance(
            text="Hello, this is a test of the Hume SDK.",
            voice=PostedUtteranceVoiceWithName(name="Salli")
        )
        
        # Create format configuration
        format_config = FormatWav(
            encoding=AudioEncoding(format="wav", sample_rate=22050),
            sample_rate=22050
        )
        
        print('✅ Configuration created')
        
        # Test streaming
        print('🔄 Testing streaming...')
        chunk_count = 0
        audio_size = 0
        
        for chunk in tts_client.synthesize_json_streaming(
            utterances=[utterance],
            format=format_config,
            strip_headers=True,
            instant_mode=True
        ):
            chunk_count += 1
            print(f'📦 Received chunk {chunk_count}: {type(chunk)}')
            
            if hasattr(chunk, 'audio') and chunk.audio:
                audio_size += len(chunk.audio)
                print(f'🎵 Audio chunk {chunk_count}, size: {len(chunk.audio)} bytes')
            else:
                print(f'📄 Non-audio chunk {chunk_count}')
        
        print(f'✅ Finished streaming: {chunk_count} chunks, {audio_size} bytes total')
        return chunk_count > 0
        
    except Exception as e:
        print(f'❌ Error during test: {e}')
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("🧪 Testing Hume SDK Directly")
    print("=" * 50)
    
    success = test_hume_sdk_direct()
    
    print("=" * 50)
    if success:
        print("✅ Hume SDK test passed!")
        sys.exit(0)
    else:
        print("❌ Hume SDK test failed!")
        sys.exit(1)