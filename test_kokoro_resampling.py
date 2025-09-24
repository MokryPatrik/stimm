#!/usr/bin/env python3
"""
Test script for Kokoro TTS provider with real-time audio resampling
"""

import asyncio
import websockets
import json
import wave
import numpy as np
from scipy import signal
import time

async def test_kokoro_resampling():
    """Test Kokoro TTS with resampling to verify audio speed is correct."""
    
    # WebSocket URL for live streaming
    uri = "ws://localhost:8000/api/tts/stream"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to TTS WebSocket")
            
            # Send initialization for live streaming
            init_payload = {
                "voice": "af_sarah",
                "language": "fr-fr", 
                "speed": 0.8
            }
            await websocket.send(json.dumps(init_payload))
            print(f"📤 Sent initialization: {init_payload}")
            
            # Wait for ready signal
            ready_msg = await websocket.recv()
            ready_data = json.loads(ready_msg)
            if ready_data.get("type") != "ready":
                raise RuntimeError(f"Expected ready signal, got: {ready_data}")
            print("✅ Live streaming ready")
            
            # Test text that should have a specific duration
            test_text = "Bonjour, je suis un test de synthèse vocale avec la nouvelle vitesse ajustée."
            print(f"📤 Sending test text: '{test_text}'")
            
            # Send text chunk
            await websocket.send(test_text)
            
            # Send end signal
            await websocket.send("")
            
            # Collect audio chunks
            audio_chunks = []
            chunk_count = 0
            
            try:
                while True:
                    # First receive control message
                    control_msg = await websocket.recv()
                    
                    if isinstance(control_msg, bytes):
                        # Binary audio data
                        audio_chunks.append(control_msg)
                        chunk_count += 1
                        print(f"🎵 Received audio chunk {chunk_count}: {len(control_msg)} bytes")
                    else:
                        # JSON control message
                        try:
                            control_data = json.loads(control_msg)
                            
                            if control_data.get("type") == "audio":
                                # Next message should be binary audio
                                audio_data = await websocket.recv()
                                if isinstance(audio_data, bytes):
                                    audio_chunks.append(audio_data)
                                    chunk_count += 1
                                    print(f"🎵 Received audio chunk {chunk_count}: {len(audio_data)} bytes")
                            elif control_data.get("type") == "end":
                                print(f"✅ Live streaming completed: {chunk_count} audio chunks")
                                break
                            elif control_data.get("type") == "error":
                                error_msg = control_data.get("message", "Unknown error")
                                print(f"❌ Live streaming error: {error_msg}")
                                break
                        except json.JSONDecodeError:
                            if isinstance(control_msg, bytes):
                                audio_chunks.append(control_msg)
                                chunk_count += 1
                                print(f"🎵 Received audio chunk {chunk_count}: {len(control_msg)} bytes")
                            
            except websockets.exceptions.ConnectionClosed:
                print("🔌 WebSocket connection closed normally")
            
            print(f"✅ Received {chunk_count} audio chunks, total {sum(len(chunk) for chunk in audio_chunks)} bytes")
            
            # Save audio to file for analysis
            if audio_chunks:
                combined_audio = b''.join(audio_chunks)
                
                # Save as WAV file with 44.1kHz sample rate
                with wave.open("test_kokoro_resampled.wav", "wb") as wav_file:
                    wav_file.setnchannels(1)  # Mono
                    wav_file.setsampwidth(2)  # 16-bit PCM
                    wav_file.setframerate(44100)  # Resampled to 44.1kHz
                    wav_file.writeframes(combined_audio)
                
                print(f"💾 Audio saved to test_kokoro_resampled.wav ({len(combined_audio)} bytes)")
                
                # Analyze the audio duration
                duration_seconds = len(combined_audio) / (44100 * 2)  # 44.1kHz, 16-bit = 2 bytes per sample
                print(f"⏱️ Audio duration: {duration_seconds:.2f} seconds")
                
                # Expected duration for normal speed (approx 1.5-2 seconds for this text)
                if 1.0 <= duration_seconds <= 3.0:
                    print("✅ Audio speed appears normal (not 2x accelerated)")
                else:
                    print(f"⚠️ Audio duration unexpected: {duration_seconds:.2f}s")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def test_resampling_function():
    """Test the resampling function directly with synthetic audio."""
    print("\n🧪 Testing resampling function directly...")
    
    # Create synthetic 24kHz audio (1 second of sine wave)
    sample_rate_24k = 24000
    duration = 1.0
    t = np.linspace(0, duration, int(sample_rate_24k * duration), endpoint=False)
    sine_wave = np.sin(2 * np.pi * 440 * t)  # 440 Hz sine wave
    
    # Convert to 16-bit PCM
    audio_16bit = (sine_wave * 32767).astype(np.int16)
    audio_bytes = audio_16bit.tobytes()
    
    print(f"Original audio: {len(audio_bytes)} bytes at 24kHz")
    
    # Test resampling
    from src.voicebot_app.services.tts.providers.kokoro_local.kokoro_local_provider import KokoroLocalProvider
    
    provider = KokoroLocalProvider()
    resampled_bytes = provider._resample_audio_chunk(audio_bytes)
    
    print(f"Resampled audio: {len(resampled_bytes)} bytes at 44.1kHz")
    
    # Calculate expected size ratio
    expected_ratio = 44100 / 24000  # 1.8375
    actual_ratio = len(resampled_bytes) / len(audio_bytes)
    
    print(f"Expected size ratio: {expected_ratio:.4f}")
    print(f"Actual size ratio: {actual_ratio:.4f}")
    
    if abs(actual_ratio - expected_ratio) < 0.01:
        print("✅ Resampling ratio is correct")
    else:
        print(f"⚠️ Resampling ratio mismatch: expected {expected_ratio:.4f}, got {actual_ratio:.4f}")

if __name__ == "__main__":
    print("🧪 Testing Kokoro TTS provider with real-time audio resampling...")
    
    # Test the resampling function directly first
    test_resampling_function()
    
    # Then test the full integration
    print("\n🧪 Testing full Kokoro TTS integration...")
    asyncio.run(test_kokoro_resampling())