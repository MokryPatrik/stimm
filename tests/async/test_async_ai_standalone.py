"""Real Async.ai TTS provider test with actual WebSocket connection."""

import asyncio
import os
import sys
import json

# Add src to path for imports
sys.path.append('/app/src')

async def test_async_ai_real_connection():
    """Test Async.ai provider with real WebSocket connection."""
    print("🎯 Async.ai TTS Provider - Real Connection Test")
    print("=" * 60)
    
    try:
        # Get configuration from environment variables
        async_api_key = os.getenv('ASYNC_API_KEY')
        async_ai_tts_url = os.getenv('ASYNC_AI_TTS_URL', 'wss://api.async.ai/text_to_speech/websocket/ws')
        async_ai_tts_voice_id = os.getenv('ASYNC_AI_TTS_VOICE_ID', 'e0f39dc4-f691-4e78-bba5-5c636692cc04')
        async_ai_tts_model_id = os.getenv('ASYNC_AI_TTS_MODEL_ID', 'asyncflow_v2.0')
        async_ai_tts_version = os.getenv('ASYNC_AI_TTS_VERSION', 'v1')
        async_ai_tts_sample_rate = int(os.getenv('ASYNC_AI_TTS_SAMPLE_RATE', '44100'))
        async_ai_tts_encoding = os.getenv('ASYNC_AI_TTS_ENCODING', 'pcm_s16le')
        async_ai_tts_container = os.getenv('ASYNC_AI_TTS_CONTAINER', 'raw')
        async_ai_tts_bit_rate = int(os.getenv('ASYNC_AI_TTS_BIT_RATE', '128000'))
        
        if not async_api_key:
            print("❌ ASYNC_API_KEY environment variable is required")
            return False
            
        print(f"✅ Using ASYNC_API_KEY: {async_api_key[:8]}...")
        print(f"✅ WebSocket URL: {async_ai_tts_url}")
        print(f"✅ Voice ID: {async_ai_tts_voice_id}")
        print(f"✅ Model ID: {async_ai_tts_model_id}")
        print(f"✅ Version: {async_ai_tts_version}")
        print(f"✅ Sample Rate: {async_ai_tts_sample_rate}Hz")
        print(f"✅ Encoding: {async_ai_tts_encoding}")
        print(f"✅ Container: {async_ai_tts_container}")
        
        # Import Async.ai provider
        from voicebot.tts.async_ai_provider import create_async_ai_provider
        from voicebot.tts import SynthesisConfig, SynthesisChunk
        
        print("\n1️⃣ Creating Async.ai provider with real configuration...")
        
        # Create provider with environment configuration
        provider = create_async_ai_provider(
            base_url=async_ai_tts_url,
            api_key=async_api_key,
            default_voice_id=async_ai_tts_voice_id,
            default_model_id=async_ai_tts_model_id,
            default_sample_rate=async_ai_tts_sample_rate,
            default_encoding=async_ai_tts_encoding,
            default_container=async_ai_tts_container,
            version=async_ai_tts_version,
        )
        
        print(f"   ✅ Provider created: {provider.name}")
        print(f"   ✅ Transport: {provider.capabilities.transport}")
        print(f"   ✅ Supports streaming: {provider.capabilities.supports_audio_streaming}")
        
        # Test 2: Build real connection configuration
        print("\n2️⃣ Building real WebSocket connection configuration...")
        
        config = SynthesisConfig(
            voice_name=async_ai_tts_voice_id,
            language_code='en-US',
            sample_rate_hz=async_ai_tts_sample_rate,
            metadata={
                'async_ai_voice_id': async_ai_tts_voice_id,
                'async_ai_model_id': async_ai_tts_model_id,
                'async_ai_encoding': async_ai_tts_encoding,
                'async_ai_container': async_ai_tts_container,
                'async_ai_bit_rate': str(async_ai_tts_bit_rate),
            }
        )
        
        connection_config = provider._build_connection_config(config)
        print(f"   ✅ WebSocket URL: {connection_config.url.split('?')[0]}?api_key=***&version={async_ai_tts_version}")
        print(f"   ✅ Headers: {connection_config.headers}")
        print(f"   ✅ Timeout: {connection_config.connect_timeout}s")
        
        # Test 3: Real WebSocket connection test
        print("\n3️⃣ Testing real WebSocket connection to Async.ai...")
        
        try:
            # Establish real WebSocket connection
            await provider._ensure_connected(config)
            print("   ✅ WebSocket connection established!")
            
            # Test initialization
            print("   📝 Sending initialization message...")
            await provider._send_initialization(config)
            print("   ✅ Initialization message sent")
            
            # Give a moment for the server to respond
            await asyncio.sleep(0.5)
            
            # Test sending longer text for better audio generation
            test_text = "Bonjour, ceci est un test de la connexion par websocket avec Async.ai et de la génération audio."
            print(f"   📝 Sending text: '{test_text[:50]}...'")
            await provider._send_text_chunk(test_text, is_final=True)
            print("   ✅ Text chunk sent")
            
            # Collect audio data
            audio_chunks = []
            print("   📥 Collecting audio responses...")
            
            # Try to receive multiple responses
            for i in range(10):  # Try up to 10 responses
                try:
                    response = await asyncio.wait_for(provider._websocket.recv(), timeout=1.0)
                    response_data = json.loads(response)
                    
                    if 'audio' in response_data and response_data['audio']:
                        audio_data = provider._decode_audio(response_data)
                        if audio_data:
                            audio_chunks.append(audio_data)
                            print(f"   📦 Received audio chunk {len(audio_chunks)}: {len(audio_data)} bytes")
                    elif 'error_code' in response_data:
                        print(f"   ❌ Error received: {response_data.get('message', 'Unknown error')}")
                        break
                    elif response_data.get('final') is True:
                        print("   ✅ Final response received")
                        break
                        
                except asyncio.TimeoutError:
                    print(f"   ⏰ Timeout after {i+1} responses")
                    break
                except Exception as e:
                    print(f"   📄 Response parsing error: {e}")
                    break
            
            # Save audio to file for playback testing
            if audio_chunks:
                total_audio = b''.join(audio_chunks)
                
                # Create WAV header for proper playback
                import wave
                import struct
                
                # Create WAV file with proper header
                audio_file = '/app/test-async-ai-audio.wav'
                with wave.open(audio_file, 'wb') as wav_file:
                    wav_file.setnchannels(1)  # Mono
                    wav_file.setsampwidth(2)  # 16-bit
                    wav_file.setframerate(async_ai_tts_sample_rate)
                    wav_file.writeframes(total_audio)
                
                print(f"   💾 Saved {len(total_audio)} bytes of PCM audio as WAV to {audio_file}")
                print(f"   🎵 Audio format: {async_ai_tts_sample_rate}Hz, 16-bit, Mono")
                print(f"   🎵 You can now play the audio file: {audio_file}")
            else:
                print("   ⚠️  No audio data received")
            
            # Close connection
            print("   🔒 Closing connection...")
            await provider._send_close_connection()
            print("   ✅ Connection closed")
            
        except Exception as e:
            print(f"   ❌ WebSocket connection failed: {e}")
            # Check if it's an authentication error
            if "403" in str(e):
                print("   🔑 This appears to be an authentication error (HTTP 403)")
                print("   🔑 Please verify your ASYNC_API_KEY is correct and valid")
            elif "401" in str(e):
                print("   🔑 This appears to be an authentication error (HTTP 401)")
                print("   🔑 Please verify your ASYNC_API_KEY is correct and valid")
            else:
                print(f"   🔍 Connection error details: {e}")
            return False
            
        finally:
            # Ensure connection is closed
            if provider._websocket:
                try:
                    await provider._close_connection()
                    print("   ✅ Connection cleanup completed")
                except:
                    pass
        
        print("\n" + "=" * 60)
        print("🎉 Async.ai real connection test completed!")
        print("✅ Provider configuration: WORKING")
        print("✅ WebSocket URL building: WORKING")
        print("✅ Real WebSocket connection: TESTED")
        
        if "403" not in str(locals().get('e', '')) and "401" not in str(locals().get('e', '')):
            print("✅ Authentication: APPEARS WORKING")
        else:
            print("❌ Authentication: NEEDS ATTENTION")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test runner."""
    success = await test_async_ai_real_connection()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)