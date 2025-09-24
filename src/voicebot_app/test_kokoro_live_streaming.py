#!/usr/bin/env python3
"""
Test script for Kokoro TTS Live Streaming
"""

import asyncio
import websockets
import json
import time
import wave

async def test_kokoro_live_streaming():
    """Test the Kokoro live streaming WebSocket endpoint"""
    
    # Test the live streaming endpoint
    uri = "ws://kokoro-tts:5000/ws/tts/live"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to Kokoro Live Streaming WebSocket")
            
            # Send initialization
            init_payload = {
                "voice": "ff_siwis",
                "language": "fr-fr",
                "speed": 0.8
            }
            await websocket.send(json.dumps(init_payload))
            print(f"📤 Sent initialization: {init_payload}")
            
            # Wait for ready signal
            ready_msg = await websocket.recv()
            ready_data = json.loads(ready_msg)
            print(f"📥 Received ready signal: {ready_data}")
            
            # Test text chunks to simulate LLM streaming
            test_chunks = [
                "Bonjour, ",
                "je suis un test ",
                "de streaming en temps réel ",
                "avec le service Kokoro TTS."
            ]
            
            audio_chunks = []
            chunk_count = 0
            start_time = time.time()
            
            # Send text chunks with realistic timing
            for i, chunk in enumerate(test_chunks):
                print(f"📤 Sending text chunk {i+1}: '{chunk}'")
                await websocket.send(chunk)
                
                # Simulate LLM generation delay
                await asyncio.sleep(0.1)
                
                # Try to receive any available audio
                try:
                    # Set a short timeout to check for immediate audio
                    audio_data = await asyncio.wait_for(websocket.recv(), timeout=0.5)
                    
                    if isinstance(audio_data, bytes):
                        # This is binary audio data
                        chunk_count += 1
                        audio_chunks.append(audio_data)
                        current_time = time.time() - start_time
                        print(f"🎵 Received audio chunk {chunk_count} at {current_time:.2f}s: {len(audio_data)} bytes")
                    else:
                        # This might be a control message
                        try:
                            control_data = json.loads(audio_data)
                            print(f"📥 Control message: {control_data}")
                        except:
                            print(f"⚠️ Unexpected non-binary data: {audio_data}")
                    
                except asyncio.TimeoutError:
                    print(f"⏰ No immediate audio for chunk {i+1} (expected for first chunks)")
            
            # Send end signal
            print("📤 Sending end signal")
            await websocket.send("")
            
            # Receive remaining audio chunks
            while True:
                try:
                    data = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    
                    if isinstance(data, bytes):
                        # Binary audio data
                        chunk_count += 1
                        audio_chunks.append(data)
                        current_time = time.time() - start_time
                        print(f"🎵 Received audio chunk {chunk_count} at {current_time:.2f}s: {len(data)} bytes")
                    else:
                        # Control message
                        try:
                            control_data = json.loads(data)
                            
                            if control_data.get("type") == "end":
                                print(f"✅ Stream completed: {control_data}")
                                break
                                
                            elif control_data.get("type") == "error":
                                print(f"❌ Error: {control_data}")
                                break
                            else:
                                print(f"📥 Control message: {control_data}")
                                
                        except json.JSONDecodeError:
                            print(f"⚠️ Unexpected non-binary data: {data}")
                        
                except asyncio.TimeoutError:
                    print("⏰ Timeout waiting for end signal")
                    break
            
            total_time = time.time() - start_time
            print(f"⏱️ Total test time: {total_time:.2f}s")
            print(f"📊 Received {chunk_count} audio chunks, total {sum(len(chunk) for chunk in audio_chunks)} bytes")
            
            # Save audio to file for verification
            if audio_chunks:
                combined_audio = b''.join(audio_chunks)
                
                # Save as WAV file
                with wave.open("test_kokoro_live_streaming.wav", "wb") as wav_file:
                    wav_file.setnchannels(1)  # Mono
                    wav_file.setsampwidth(2)  # 16-bit PCM
                    wav_file.setframerate(24000)  # Sample rate
                    wav_file.writeframes(combined_audio)
                
                print(f"💾 Audio saved to test_kokoro_live_streaming.wav ({len(combined_audio)} bytes)")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def test_voicebot_live_streaming():
    """Test the voicebot live streaming endpoint"""
    
    uri = "ws://localhost:8001/api/tts/ws/live"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to Voicebot Live Streaming WebSocket")
            
            # Test text chunks
            test_chunks = [
                "Bonjour, ",
                "ceci est un test ",
                "de streaming en direct ",
                "avec le nouveau protocole."
            ]
            
            audio_chunks = []
            chunk_count = 0
            start_time = time.time()
            
            # Send text chunks
            for i, chunk in enumerate(test_chunks):
                print(f"📤 Sending text chunk {i+1}: '{chunk}'")
                await websocket.send(chunk)
                await asyncio.sleep(0.1)  # Simulate LLM delay
                
                # Try to receive audio immediately
                try:
                    audio_data = await asyncio.wait_for(websocket.recv(), timeout=0.5)
                    if isinstance(audio_data, bytes):
                        chunk_count += 1
                        audio_chunks.append(audio_data)
                        current_time = time.time() - start_time
                        print(f"🎵 Received audio chunk {chunk_count} at {current_time:.2f}s: {len(audio_data)} bytes")
                except asyncio.TimeoutError:
                    print(f"⏰ No immediate audio for chunk {i+1}")
            
            # Send end signal
            await websocket.send("")
            
            # Receive remaining audio
            try:
                while True:
                    try:
                        audio_data = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        if isinstance(audio_data, bytes):
                            chunk_count += 1
                            audio_chunks.append(audio_data)
                            current_time = time.time() - start_time
                            print(f"🎵 Received final audio chunk {chunk_count} at {current_time:.2f}s: {len(audio_data)} bytes")
                    except asyncio.TimeoutError:
                        print("✅ Stream completed (timeout)")
                        break
            except websockets.exceptions.ConnectionClosedOK:
                print("✅ Stream completed (WebSocket closed normally)")
            except Exception as e:
                print(f"⚠️ Unexpected error: {e}")
            
            total_time = time.time() - start_time
            print(f"⏱️ Voicebot live streaming total time: {total_time:.2f}s")
            print(f"📊 Received {chunk_count} audio chunks")
            
    except Exception as e:
        print(f"❌ Voicebot live streaming error: {e}")
        import traceback
        traceback.print_exc()

async def main():
    print("🧪 Testing Kokoro TTS Live Streaming Implementation...")
    print("=" * 60)
    
    print("1. Testing Kokoro Service Live Streaming...")
    await test_kokoro_live_streaming()
    
    print("\n" + "=" * 60)
    print("2. Testing Voicebot Live Streaming Integration...")
    await test_voicebot_live_streaming()
    
    print("\n" + "=" * 60)
    print("✅ Live streaming tests completed!")

if __name__ == "__main__":
    asyncio.run(main())