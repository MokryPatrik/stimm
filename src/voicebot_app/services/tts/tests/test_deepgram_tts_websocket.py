#!/usr/bin/env python3
"""
Test script for Deepgram TTS WebSocket integration
"""

import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_deepgram_tts():
    """Test Deepgram TTS through WebSocket interface"""
    
    uri = "ws://localhost:8001/api/tts/ws"
    
    try:
        logger.info(f"Connecting to TTS WebSocket: {uri}")
        async with websockets.connect(uri) as websocket:
            logger.info("✅ WebSocket connected")
            
            # Test text to send
            test_texts = [
                "Hello, this is a test of Deepgram TTS.",
                "Does it work now with the correct authentication?",
                "Let's see if we get audio chunks back."
            ]
            
            audio_chunk_count = 0
            
            for text in test_texts:
                logger.info(f"📤 Sending text: '{text}'")
                await websocket.send(text)
                
                # Wait for audio response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    
                    if isinstance(response, bytes):
                        audio_chunk_count += 1
                        logger.info(f"🎵 Received audio chunk {audio_chunk_count}: {len(response)} bytes")
                    else:
                        logger.info(f"📄 Received non-audio response: {response}")
                        
                except asyncio.TimeoutError:
                    logger.warning("⏰ Timeout waiting for audio response")
            
            # Send end of stream signal
            await websocket.send("")
            logger.info("📤 Sent end of stream signal")
            
            # Wait for final responses
            try:
                while True:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    if isinstance(response, bytes):
                        audio_chunk_count += 1
                        logger.info(f"🎵 Received final audio chunk {audio_chunk_count}: {len(response)} bytes")
                    else:
                        logger.info(f"📄 Received final message: {response}")
            except asyncio.TimeoutError:
                logger.info("✅ No more responses, stream complete")
            
            logger.info(f"🎯 Test completed: {audio_chunk_count} audio chunks received")
            
    except Exception as e:
        logger.error(f"❌ WebSocket test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_deepgram_tts())