"""Detailed debug test for Hume SDK."""

import os
import sys
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from hume import HumeClient
from hume.tts import AudioEncoding, FormatWav, PostedUtterance, PostedUtteranceVoiceWithName


def test_hume_sdk_detailed():
    """Test Hume SDK with detailed debugging."""
    api_key = os.getenv('HUME_API_KEY')
    print(f'API Key present: {bool(api_key)}')
    if api_key:
        print(f'API Key length: {len(api_key)}')
        print(f'API Key prefix: {api_key[:10]}...')
    else:
        print('❌ HUME_API_KEY not found')
        return False
    
    try:
        # Create Hume client
        print('\n1. Creating Hume client...')
        client = HumeClient(api_key=api_key)
        print('✅ Client created')
        
        print('\n2. Getting TTS client...')
        tts_client = client.tts
        print(f'✅ TTS client: {type(tts_client)}')
        
        # Create utterance
        print('\n3. Creating utterance...')
        utterance = PostedUtterance(
            text="Hello world",
            voice=PostedUtteranceVoiceWithName(name="Salli")
        )
        print(f'✅ Utterance: {utterance}')
        
        # Create format configuration
        print('\n4. Creating format config...')
        format_config = FormatWav(
            encoding=AudioEncoding(format="wav", sample_rate=22050),
            sample_rate=22050
        )
        print(f'✅ Format config: {format_config}')
        
        # Test streaming
        print('\n5. Calling synthesize_json_streaming...')
        try:
            streaming_result = tts_client.synthesize_json_streaming(
                utterances=[utterance],
                format=format_config,
                strip_headers=True,
                instant_mode=True
            )
            print(f'✅ Streaming result type: {type(streaming_result)}')
            print(f'   Streaming result: {streaming_result}')
            
            # Check if it's a generator/iterator
            print(f'   Is iterator: {hasattr(streaming_result, "__iter__")}')
            print(f'   Is generator: {hasattr(streaming_result, "__next__")}')
            
            print('\n6. Iterating over chunks...')
            chunk_count = 0
            audio_count = 0
            
            for chunk in streaming_result:
                chunk_count += 1
                print(f'\n   Chunk {chunk_count}:')
                print(f'   - Type: {type(chunk)}')
                print(f'   - Attributes: {dir(chunk)}')
                
                if hasattr(chunk, 'audio'):
                    if chunk.audio:
                        audio_count += 1
                        print(f'   - Audio size: {len(chunk.audio)} bytes')
                    else:
                        print(f'   - Audio: None or empty')
                else:
                    print(f'   - No audio attribute')
                
                # Print other attributes
                for attr in ['text', 'status', 'error']:
                    if hasattr(chunk, attr):
                        print(f'   - {attr}: {getattr(chunk, attr)}')
            
            print(f'\n✅ Finished: {chunk_count} chunks, {audio_count} with audio')
            return chunk_count > 0
            
        except Exception as stream_error:
            print(f'❌ Streaming error: {stream_error}')
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("=" * 70)
    print("🔍 Detailed Hume SDK Debug Test")
    print("=" * 70)
    
    success = test_hume_sdk_detailed()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ Test completed successfully!")
        sys.exit(0)
    else:
        print("❌ Test failed!")
        sys.exit(1)