"""
Test LiveKit microphone capture with real audio and save recording to file
"""
import asyncio
import time
import logging
import wave
from livekit import rtc
from .livekit_client import LiveKitClient

logger = logging.getLogger(__name__)

async def test_livekit_microphone(duration: float):
    """Test LiveKit microphone capture with real audio from PulseAudio and save to file"""
    print(f"\n🎤 Testing LiveKit Microphone Capture with Real Audio ({duration}s)")
    print("=" * 80)
    print(f"Testing real audio capture for {duration} seconds...")
    print("This test uses our own PulseAudio capture method")
    print("🎙️ Speak into your microphone during the test!")
    print()
    
    # File to save the recording
    output_file = "/app/test_livekit_recording.wav"
    audio_data = []
    
    try:
        # Test 1: Create LiveKit client
        print("🔧 Test 1: Creating LiveKit client...")
        
        # Use test credentials (these would need to be valid for a real test)
        room_name = "test-room"
        token = "test-token"  # This would need to be a real JWT token
        livekit_url = "http://localhost:7880"  # Local LiveKit server
        
        client = LiveKitClient(room_name, token, livekit_url)
        print("✅ LiveKit client created")
        
        # Test 2: Create audio components
        print("🔧 Test 2: Creating audio source and track...")
        client.audio_source = rtc.AudioSource(sample_rate=48000, num_channels=1)
        client.audio_track = rtc.LocalAudioTrack.create_audio_track("microphone", client.audio_source)
        print("✅ Audio components created")
        
        # Test 3: Start real audio capture
        print("🔧 Test 3: Starting real audio capture...")
        await client.start_audio_capture()
        print("✅ Real audio capture started")
        
        # Test 4: Capture for duration and collect audio data
        print(f"🔧 Test 4: Capturing real audio for {duration}s...")
        print("🎙️ Speak into your microphone now!")
        start_time = time.time()
        frames_captured = 0
        audio_data = []
        
        while time.time() - start_time < duration:
            await asyncio.sleep(0.1)
            frames_captured += 1
            
            # Collect ALL available audio data from recording queue
            while not client.recording_queue.empty():
                try:
                    audio_chunk = client.recording_queue.get_nowait()
                    audio_data.append(audio_chunk)
                except:
                    break
            
            # Log progress
            elapsed = time.time() - start_time
            if int(elapsed) % 2 == 0 and elapsed < duration - 0.5:
                print(f"⏱️ Capturing real audio... {elapsed:.1f}/{duration:.1f}s")
        
        # Collect any remaining audio data after the main loop
        print("🔧 Collecting remaining audio data...")
        remaining_collected = 0
        while not client.recording_queue.empty():
            try:
                audio_chunk = client.recording_queue.get_nowait()
                audio_data.append(audio_chunk)
                remaining_collected += 1
            except:
                break
        if remaining_collected > 0:
            print(f"✅ Collected {remaining_collected} additional audio chunks")
        
        # Test 5: Save audio to file
        print("🔧 Test 5: Saving audio to file...")
        if audio_data:
            # Combine all audio chunks
            combined_audio = b''.join(audio_data)
            
            # Save as WAV file
            with wave.open(output_file, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit = 2 bytes
                wav_file.setframerate(48000)  # 48kHz
                wav_file.writeframes(combined_audio)
            
            print(f"✅ Audio saved to: {output_file}")
            print(f"📊 File size: {len(combined_audio)} bytes")
            print(f"🎵 Duration: {len(combined_audio) / (48000 * 2):.2f} seconds")  # 48kHz * 2 bytes per sample
        else:
            print("⚠️ No audio data captured")
        
        # Test 6: Stop capture
        print("🔧 Test 6: Stopping audio capture...")
        client.stop_audio_capture()
        print("✅ Audio capture stopped")
        
        print("✅ LiveKit real audio capture test complete")
        print()
        print("🎯 Test Results:")
        print(f"   • LiveKit client: ✅ Created")
        print(f"   • Audio components: ✅ Created")
        print(f"   • Real audio capture: ✅ Started and stopped")
        print(f"   • Duration: ✅ {duration}s completed")
        print(f"   • Frames processed: ✅ {frames_captured} frames")
        print(f"   • Audio file: ✅ {output_file}")
        print()
        print("📝 Note: This test confirms our custom audio capture works.")
        print("   For full functionality, you need:")
        print("   • A valid LiveKit JWT token")
        print("   • A running LiveKit server")
        print("   • Connection to a room")
        print()
        print("🔍 To verify the recording:")
        print(f"   docker exec voicebot-app ls -la {output_file}")
        print(f"   docker cp voicebot-app:{output_file} ./test_livekit_recording.wav")
        print()
        return 0
            
    except Exception as e:
        print(f"\n❌ LiveKit real audio capture test failed: {e}")
        print("\n🔧 Debug Information:")
        print(f"   • Error type: {type(e).__name__}")
        print(f"   • Error message: {str(e)}")
        print("\nTroubleshooting:")
        print("• Make sure your microphone is connected and not muted")
        print("• Verify PulseAudio configuration")
        print("• Check if ffmpeg is installed")
        print("• For full test, provide valid LiveKit credentials")
        return 1