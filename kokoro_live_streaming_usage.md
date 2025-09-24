# Kokoro TTS Live Streaming Usage Guide

## Overview

The new live streaming implementation enables real-time audio generation with Kokoro TTS, significantly reducing latency from 6 seconds to 2-3 seconds by processing text chunks incrementally rather than waiting for the complete LLM response.

## New Endpoints

### 1. Kokoro Service Live Streaming
**WebSocket URL**: `ws://localhost:5000/ws/tts/live`

**Protocol**:
- **Initialization**: Send JSON with voice, language, speed
- **Text Streaming**: Send text chunks directly (no JSON wrapper)
- **Audio Streaming**: Receive JSON control messages + binary audio chunks
- **End Signal**: Send empty string to complete stream

### 2. Voicebot Live Streaming
**WebSocket URL**: `ws://localhost:8001/tts/ws/live`

**Protocol**: Same as standard TTS WebSocket but uses live streaming internally

## Usage Examples

### Direct Kokoro Service Usage

```python
import asyncio
import websockets
import json

async def kokoro_live_streaming_example():
    uri = "ws://localhost:5000/ws/tts/live"
    
    async with websockets.connect(uri) as websocket:
        # Initialize
        init_payload = {
            "voice": "ff_siwis",
            "language": "fr-fr",
            "speed": 0.8
        }
        await websocket.send(json.dumps(init_payload))
        
        # Wait for ready signal
        ready_msg = await websocket.recv()
        ready_data = json.loads(ready_msg)
        
        # Stream text chunks
        text_chunks = [
            "Bonjour, ",
            "je suis un test ",
            "de streaming en temps réel."
        ]
        
        for chunk in text_chunks:
            await websocket.send(chunk)
            await asyncio.sleep(0.1)  # Simulate LLM delay
            
            # Receive audio immediately
            try:
                control_msg = await asyncio.wait_for(websocket.recv(), timeout=0.5)
                control_data = json.loads(control_msg)
                
                if control_data.get("type") == "audio":
                    audio_data = await websocket.recv()
                    # Process audio chunk immediately
                    print(f"Received audio: {len(audio_data)} bytes")
            except asyncio.TimeoutError:
                pass
        
        # End stream
        await websocket.send("")
```

### Voicebot Integration

The voicebot service automatically uses live streaming when available. No code changes needed in the frontend - it will automatically benefit from reduced latency.

## Performance Benefits

### Before (Buffered Streaming)
- **First Audio**: 3-4 seconds after LLM completes
- **Total Latency**: 6 seconds
- **User Experience**: Noticeable delay

### After (Live Streaming)
- **First Audio**: 200-500ms after first words
- **Total Latency**: 2-3 seconds
- **User Experience**: Responsive conversation

## Configuration

### Environment Variables
The system automatically detects and uses live streaming when available. No additional configuration needed.

### Fallback Behavior
If live streaming is not supported by the provider, the system automatically falls back to standard streaming.

## Testing

### Test Script
Use the provided test script to verify live streaming functionality:

```bash
python test_kokoro_live_streaming.py
```

### Manual Testing
1. Ensure Kokoro service is running: `docker-compose up kokoro-tts`
2. Test direct endpoint: Connect to `ws://localhost:5000/ws/tts/live`
3. Test voicebot integration: Connect to `ws://localhost:8001/tts/ws/live`

## Troubleshooting

### Common Issues

1. **Connection Refused**: Ensure Kokoro service is running on port 5000
2. **No Audio Received**: Check Kokoro service logs for synthesis errors
3. **Protocol Errors**: Verify text chunks are sent as plain text, not JSON

### Logging
Enable debug logging for detailed information:

```bash
export LOG_LEVEL=DEBUG
```

## Migration Guide

### For Existing Users
- No breaking changes - existing code continues to work
- Live streaming is automatically used when available
- Performance improvements are automatic

### For New Implementations
- Use the live streaming endpoints for better performance
- Follow the new protocol for direct Kokoro service integration
- The voicebot service handles everything automatically

## Technical Details

### Protocol Flow
1. **Initialization**: Client sends voice configuration
2. **Ready Signal**: Server confirms readiness
3. **Text Streaming**: Client sends text chunks incrementally
4. **Audio Streaming**: Server sends audio chunks immediately
5. **Completion**: Client sends empty string to end stream

### Error Handling
- JSON control messages include error information
- Timeout handling for network issues
- Automatic fallback to standard streaming if live streaming fails