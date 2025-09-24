# Kokoro Live Streaming Implementation Plan

## Architecture Overview

Based on your feedback, we need to build a **true live streaming WebSocket wrapper** around Kokoro that streams audio frames as they're generated, rather than using the buffered async.ai compatible approach.

## Proposed Architecture

### WebSocket Protocol Design

#### Control Messages (JSON)
```json
{
  "type": "ready",
  "sample_rate": 24000,
  "format": "pcm_s16le"
}
```

```json
{
  "type": "audio",
  "chunk_id": 1,
  "size": 1024
}
```

```json
{
  "type": "end",
  "total_chunks": 50
}
```

```json
{
  "type": "error",
  "message": "Synthesis failed"
}
```

#### Audio Frames (Binary)
- Raw PCM 16-bit mono
- 24kHz sample rate (default)
- One WebSocket message per audio chunk
- Aligned 1:1 with "audio" control messages

### Implementation Strategy

## Phase 1: Live Streaming WebSocket Endpoint

### New WebSocket Route: `/ws/tts/live`

```python
@app.websocket("/ws/tts/live")
async def websocket_tts_live(websocket: WebSocket):
    """True live streaming WebSocket endpoint for Kokoro TTS"""
    await handle_live_streaming_connection(websocket)
```

### Live Streaming Handler

```python
async def handle_live_streaming_connection(websocket: WebSocket):
    await websocket.accept()
    
    try:
        # Wait for initialization
        init_data = await websocket.receive_json()
        voice_id = init_data.get("voice", "ff_siwis")
        language = init_data.get("language", "fr-fr")
        speed = init_data.get("speed", 0.8)
        
        # Send ready signal
        await websocket.send_json({
            "type": "ready",
            "sample_rate": 24000,
            "format": "pcm_s16le"
        })
        
        # Process text chunks incrementally
        async for text_chunk in receive_text_chunks(websocket):
            if text_chunk:
                await stream_audio_incrementally(
                    websocket, text_chunk, voice_id, language, speed
                )
        
        # Send end signal
        await websocket.send_json({
            "type": "end",
            "message": "Stream completed"
        })
        
    except Exception as e:
        await websocket.send_json({
            "type": "error", 
            "message": str(e)
        })
```

### Incremental Audio Streaming

```python
async def stream_audio_incrementally(websocket, text_chunk, voice_id, language, speed):
    """Stream audio for a text chunk as it's generated"""
    
    # Use Kokoro's create_stream with the text chunk
    model = await _load_model()
    
    chunk_id = 0
    async for samples, sample_rate in model.create_stream(
        text_chunk,
        voice=voice_id,
        speed=speed,
        lang=language,
    ):
        # Convert to PCM16
        pcm_data = _audio_to_pcm16(samples)
        
        if pcm_data:
            chunk_id += 1
            
            # Send audio control message
            await websocket.send_json({
                "type": "audio",
                "chunk_id": chunk_id,
                "size": len(pcm_data)
            })
            
            # Send binary audio data
            await websocket.send_bytes(pcm_data)
```

## Phase 2: Updated KokoroLocalProvider

### New Streaming Method

```python
class KokoroLocalProvider:
    async def live_stream_synthesis(self, text_generator: AsyncGenerator[str, None]) -> AsyncGenerator[bytes, None]:
        """True live streaming implementation"""
        url = self.config.kokoro_local_url.replace("/stream", "/live")
        
        async with websockets.connect(url) as ws:
            # Send initialization
            init_msg = {
                "voice": self.voice_id,
                "language": self.language, 
                "speed": self.speed
            }
            await ws.send(json.dumps(init_msg))
            
            # Wait for ready signal
            ready_msg = await ws.recv()
            ready_data = json.loads(ready_msg)
            assert ready_data["type"] == "ready"
            
            # Process text and audio concurrently
            queue = asyncio.Queue()
            
            async def sender():
                async for text_chunk in text_generator:
                    await ws.send(text_chunk)
                await ws.send("")  # End signal
            
            async def receiver():
                while True:
                    # First receive control message
                    control_msg = await ws.recv()
                    control_data = json.loads(control_msg)
                    
                    if control_data["type"] == "audio":
                        # Then receive binary audio data
                        audio_data = await ws.recv()
                        await queue.put(audio_data)
                    elif control_data["type"] == "end":
                        await queue.put(None)
                        break
                    elif control_data["type"] == "error":
                        raise Exception(control_data["message"])
            
            # Run both tasks
            send_task = asyncio.create_task(sender())
            recv_task = asyncio.create_task(receiver())
            
            try:
                while True:
                    item = await queue.get()
                    if item is None:
                        break
                    yield item
            finally:
                send_task.cancel()
                recv_task.cancel()
                await asyncio.gather(send_task, recv_task, return_exceptions=True)
```

## Phase 3: Integration with Voicebot

### Actual Voicebot Architecture

**Important**: The voicebot interface does **NOT** use TTS WebSocket endpoints directly. Instead:

1. **Voicebot connects to**: `/api/voicebot/stream`
2. **TTS is called directly** via `tts_service.stream_synthesis()`
3. **Audio is sent as binary** through the voicebot WebSocket connection
4. **No separate TTS WebSocket endpoints are used**

### Current TTS Routes (For Reference Only)

```python
@router.websocket("/tts/ws")
async def tts_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for TTS operations (not used by voicebot)
    """
    await websocket.accept()
    
    async def text_generator():
        while True:
            data = await websocket.receive_text()
            if data == "":
                break
            yield data
    
    async for audio_chunk in tts_service.stream_synthesis(text_generator()):
        await websocket.send_bytes(audio_chunk)
```

**Note**: The `/tts/ws/live` endpoint was removed as it was redundant and not used.

## Performance Expectations

### Latency Comparison

| Approach | First Audio Latency | Total Latency | User Experience |
|----------|---------------------|---------------|-----------------|
| Current Buffered | 3-4 seconds | 6 seconds | Noticeable delay |
| **Live Streaming** | **200-500ms** | **2-3 seconds** | **Responsive** |

### Expected Improvements

1. **First Audio**: Within 200-500ms of first text chunk
2. **Continuous Streaming**: Audio flows as text arrives
3. **Reduced Total Latency**: 50-60% reduction
4. **Natural Conversation**: No artificial pauses

## Implementation Steps

### Step 1: Implement Live WebSocket Endpoint
- Add `/ws/tts/live` route to Kokoro service
- Implement incremental audio streaming
- Test with direct WebSocket client

### Step 2: Update KokoroLocalProvider
- Add `live_stream_synthesis` method
- Implement new protocol handling
- Maintain backward compatibility

### Step 3: Integrate with Voicebot
- Add live streaming WebSocket route
- Update provider selection logic
- Test end-to-end pipeline

### Step 4: Performance Validation
- Benchmark against current implementation
- Measure first audio latency
- Validate audio quality and prosody

## Technical Considerations

### Prosody Preservation
- Kokoro may need complete sentences for natural prosody
- Consider sentence-boundary detection for optimal streaming
- Fallback to buffered mode if streaming quality poor

### Error Handling
- Network disconnections during streaming
- Kokoro model failures
- Invalid text input handling

### Backward Compatibility
- Keep existing async.ai compatible endpoint
- Allow provider to choose streaming method
- Smooth migration path

## Success Criteria

### Primary Metrics
1. **First Audio Latency**: < 500ms
2. **End-to-End Latency**: < 3 seconds
3. **Audio Quality**: Natural prosody and flow

### Secondary Metrics
1. **Error Rate**: < 1%
2. **Resource Usage**: Stable CPU/GPU utilization
3. **Concurrent Users**: Support multiple simultaneous streams

## Next Actions

1. **Switch to Code mode** to implement the live streaming endpoint
2. **Implement and test** the new WebSocket protocol
3. **Update KokoroLocalProvider** with live streaming support
4. **Benchmark performance** against current implementation
5. **Deploy and validate** in the voicebot interface

This live streaming approach addresses the fundamental buffering issue and should achieve performance comparable to async.ai while maintaining the benefits of local, self-hosted TTS.