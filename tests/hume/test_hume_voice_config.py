"""Test different Hume voice configurations to find what works."""

import os
import sys
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

from hume import HumeClient
from hume.tts import (
    AudioEncoding, 
    FormatWav, 
    PostedUtterance, 
    PostedUtteranceVoiceWithName,
    PostedUtteranceVoiceWithId
)


def test_voice_configuration(voice_config, description):
    """Test a specific voice configuration."""
    print(f"\n{'='*70}")
    print(f"Testing: {description}")
    print(f"{'='*70}")
    
    api_key = os.getenv('HUME_API_KEY')
    if not api_key:
        print('❌ HUME_API_KEY not found')
        return False
    
    try:
        client = HumeClient(api_key=api_key)
        tts_client = client.tts
        
        # Create utterance with provided voice config
        utterance = PostedUtterance(
            text="Hello, this is a test.",
            voice=voice_config
        )
        
        print(f"Utterance config: {utterance}")
        
        # Create format configuration - try 24000 Hz like in .env
        format_config = FormatWav(
            encoding=AudioEncoding(format="wav", sample_rate=24000),
            sample_rate=24000
        )
        
        # Test streaming
        chunk_count = 0
        audio_bytes = 0
        
        for chunk in tts_client.synthesize_json_streaming(
            utterances=[utterance],
            format=format_config,
            strip_headers=True,
            instant_mode=False  # Try without instant mode
        ):
            chunk_count += 1
            if hasattr(chunk, 'audio') and chunk.audio:
                audio_bytes += len(chunk.audio)
                print(f'✅ Audio chunk {chunk_count}: {len(chunk.audio)} bytes')
        
        if chunk_count > 0 and audio_bytes > 0:
            print(f'✅ SUCCESS: {chunk_count} chunks, {audio_bytes} bytes total')
            return True
        else:
            print(f'❌ FAILED: {chunk_count} chunks, {audio_bytes} bytes')
            return False
            
    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()
        return False


def main():
    """Test various voice configurations."""
    print("=" * 70)
    print("🎙️  Hume Voice Configuration Investigation")
    print("=" * 70)
    
    results = {}
    
    # Test 1: Voice ID from .env
    voice_id = os.getenv('HUME_TTS_VOICE_ID', '5b612d83-696a-4089-88a7-da3e8e8126e7')
    results['Voice ID from .env'] = test_voice_configuration(
        PostedUtteranceVoiceWithId(id=voice_id),
        f"Voice ID from .env: {voice_id}"
    )
    
    # Test 2: Voice name "Salli" (AWS Polly style)
    results['Voice name: Salli'] = test_voice_configuration(
        PostedUtteranceVoiceWithName(name="Salli"),
        "Voice name: Salli (AWS Polly style)"
    )
    
    # Test 3: Try some common Hume voice names
    for voice_name in ['ITO', 'KORA', 'DACHER', 'AURA']:
        results[f'Voice name: {voice_name}'] = test_voice_configuration(
            PostedUtteranceVoiceWithName(name=voice_name),
            f"Voice name: {voice_name} (Hume style)"
        )
    
    # Test 4: No voice specified (try default)
    results['No voice (default)'] = test_voice_configuration(
        None,
        "No voice specified (system default)"
    )
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    
    for config, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {config}")
    
    successful_configs = [k for k, v in results.items() if v]
    
    if successful_configs:
        print(f"\n✅ Found {len(successful_configs)} working configuration(s)!")
        print("Working configs:")
        for config in successful_configs:
            print(f"  - {config}")
        return 0
    else:
        print("\n❌ No working configurations found!")
        return 1


if __name__ == '__main__':
    sys.exit(main())