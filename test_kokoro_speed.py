#!/usr/bin/env python3
"""
Test script for Kokoro TTS provider with speed adjustment
"""

import asyncio
import websockets
import json
import base64
import wave
import io

async def test_kokoro_tts():
    """Test Kokoro TTS provider with speed adjustment"""
    
    # WebSocket URL
    uri = "ws://localhost:8001/tts/ws"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to TTS WebSocket")
            
            # Test text with speed adjustment
            test_text = "Bonjour, je suis un test de synthèse vocale avec la nouvelle vitesse ajustée à 0.8."
            
            # Send text in chunks to simulate streaming
            print(f"📤 Sending text: '{test_text}'")
            await websocket.send(test_text)
            
            # Send end of stream signal
            await websocket.send("")
            
            # Collect audio chunks
            audio_chunks = []
            chunk_count = 0
            
            try:
                async for audio_data in websocket:
                    if isinstance(audio_data, bytes):
                        audio_chunks.append(audio_data)
                        chunk_count += 1
                        print(f"🎵 Received audio chunk {chunk_count}: {len(audio_data)} bytes")
                    else:
                        print(f"📝 Received non-audio data: {audio_data}")
                        
            except websockets.exceptions.ConnectionClosed:
                print("🔌 WebSocket connection closed normally")
            
            print(f"✅ Received {chunk_count} audio chunks, total {sum(len(chunk) for chunk in audio_chunks)} bytes")
            
            # Save audio to file for testing
            if audio_chunks:
                combined_audio = b''.join(audio_chunks)
                
                # Save as WAV file
                with wave.open("test_kokoro_speed.wav", "wb") as wav_file:
                    wav_file.setnchannels(1)  # Mono
                    wav_file.setsampwidth(2)  # 16-bit PCM
                    wav_file.setframerate(24000)  # Sample rate
                    wav_file.writeframes(combined_audio)
                
                print(f"💾 Audio saved to test_kokoro_speed.wav ({len(combined_audio)} bytes)")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 Testing Kokoro TTS provider with speed adjustment...")
    asyncio.run(test_kokoro_tts())