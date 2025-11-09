# Async.ai TTS Provider

The Async.ai TTS provider implements a WebSocket-based streaming text-to-speech service that provides real-time, seamless audio generation with bidirectional communication capabilities.

## Overview

The Async.ai provider follows the same WebSocket pattern as other providers (Hume, ElevenLabs) and integrates seamlessly with the voicebot's streaming architecture. It supports:

- **Real-time streaming**: Audio is generated and streamed as text is processed
- **Bidirectional communication**: Supports both text input and audio output streams
- **Seamless integration**: Works with the existing voicebot streaming infrastructure
- **Configurable parameters**: Supports voice selection, audio format, and quality settings

## Configuration

### Environment Variables

The Async.ai provider can be configured through the following environment variables:

```bash
# Core configuration
TTS_PROVIDER=async.ai
TTS_API_TOKEN=your_async_ai_api_key

# Async.ai specific settings
ASYNC_AI_TTS_URL=wss://api.async.ai/text_to_speech/websocket/ws
ASYNC_AI_TTS_VOICE_ID=e0f39dc4-f691-4e78-bba5-5c636692cc04
ASYNC_AI_TTS_MODEL_ID=asyncflow_v2.0
ASYNC_AI_TTS_VERSION=v1
ASYNC_AI_TTS_SAMPLE_RATE=44100
ASYNC_AI_TTS_ENCODING=pcm_s16le
ASYNC_AI_TTS_CONTAINER=raw
ASYNC_AI_TTS_BIT_RATE=128000
```

### Configuration Parameters

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ASYNC_AI_TTS_URL` | WebSocket endpoint URL | `wss://api.async.ai/text_to_speech/websocket/ws` | No |
| `ASYNC_AI_TTS_VOICE_ID` | Default voice ID | `e0f39dc4-f691-4e78-bba5-5c636692cc04` | No |
| `ASYNC_AI_TTS_MODEL_ID` | TTS model ID | `asyncflow_v2.0` | No |
| `ASYNC_AI_TTS_VERSION` | API version | `v1` | No |
| `ASYNC_AI_TTS_SAMPLE_RATE` | Audio sample rate | `44100` | No |
| `ASYNC_AI_TTS_ENCODING` | Audio encoding format | `pcm_s16le` | No |
| `ASYNC_AI_TTS_CONTAINER` | Audio container format | `raw` | No |
| `ASYNC_AI_TTS_BIT_RATE` | Audio bit rate | `128000` | No |

## Usage

### Basic Usage

Set the provider and API token in your environment:

```bash
export TTS_PROVIDER=async.ai
export TTS_API_TOKEN=your_async_ai_api_key
```

The provider will automatically be used for TTS operations.

### Advanced Configuration

You can override default settings per-request using metadata:

```python
from voicebot.tts import SynthesisConfig

config = SynthesisConfig(
    voice_name="custom_voice",
    language_code="en-US",
    sample_rate_hz=44100,
    metadata={
        "async_ai_voice_id": "custom_voice_id",
        "async_ai_model_id": "custom_model",
        "async_ai_encoding": "pcm_f32le",
        "async_ai_container": "wav",
        "async_ai_bit_rate": "256000",
    }
)
```

## API Protocol

### WebSocket Connection

The provider connects to Async.ai using WebSocket with the following URL format:
```
wss://api.async.ai/text_to_speech/websocket/ws?api_key=YOUR_API_KEY&version=v1
```

### Message Flow

1. **Connection Initialization**: Send `initializeConnection` message with voice and format configuration
2. **Text Streaming**: Send `sendText` messages with text chunks (always ending with space)
3. **Audio Reception**: Receive `audioOutput` messages with base64-encoded audio
4. **Connection Close**: Send `closeConnection` message with empty text

### Message Types

#### Initialize Connection
```json
{
  "model_id": "asyncflow_v2.0",
  "voice": {
    "mode": "id",
    "id": "voice_id"
  },
  "output_format": {
    "container": "raw",
    "encoding": "pcm_s16le",
    "sample_rate": 44100
  }
}
```

#### Send Text
```json
{
  "transcript": "Hello world ",
  "force": false
}
```

#### Audio Output
```json
{
  "audio": "base64_encoded_audio_data",
  "final": false
}
```

## Features

### Real-time Streaming
- Audio generation starts as soon as text is received
- Supports incremental text processing
- Maintains consistent prosody across chunks

### Voice Selection
- Supports voice ID-based selection
- Configurable voice parameters
- Fallback to default voice if not specified

### Audio Format Options
- Multiple encoding formats (pcm_s16le, pcm_f32le, etc.)
- Configurable sample rates
- Raw and container format support

### Error Handling
- Comprehensive error reporting
- Graceful connection management
- Automatic reconnection on failures

## Integration

### With Voicebot Application

The provider integrates seamlessly with the voicebot application:

```python
# The provider is automatically selected based on TTS_PROVIDER
provider = _ensure_tts_provider()

# Use with streaming conversation
async for audio_chunk in provider.stream(config, text_stream):
    yield audio_chunk.data
```

### With Custom Applications

For custom applications, use the factory function:

```python
from voicebot.tts.async_ai_provider import create_async_ai_provider

provider = create_async_ai_provider(
    api_key="your_api_key",
    default_voice_id="your_voice_id",
    default_model_id="your_model_id",
)

# Use for streaming TTS
async for audio_chunk in provider.stream(config, text_stream):
    process_audio(audio_chunk.data)
```

## Testing

Run the comprehensive test suite:

```bash
# Using pytest (if available)
python -m pytest tests/test_async_ai_provider.py -v

# Using simple test script
python tests/test_async_ai_simple.py
```

## Troubleshooting

### Common Issues

1. **Connection Failed**
   - Verify API key is correct
   - Check network connectivity
   - Ensure WebSocket URL is accessible

2. **Voice Not Found**
   - Verify voice ID exists in Async.ai
   - Check voice availability for your account
   - Use default voice as fallback

3. **Audio Quality Issues**
   - Adjust sample rate and encoding settings
   - Check bit rate configuration
   - Verify audio format compatibility

### Debug Mode

Enable debug logging to troubleshoot issues:

```bash
export LOG_LEVEL=DEBUG
```

## Performance Considerations

- **Latency**: WebSocket provides lower latency than HTTP for streaming
- **Throughput**: Supports high-throughput text streaming
- **Memory**: Efficient memory usage with chunked processing
- **Network**: Optimized for stable network connections

## Comparison with Other Providers

| Feature | Async.ai | Hume | ElevenLabs |
|---------|----------|------|------------|
| Transport | WebSocket | WebSocket | WebSocket |
| Real-time Streaming | ✅ | ✅ | ✅ |
| Bidirectional | ✅ | ✅ | ✅ |
| Voice Selection | ID-based | ID/Name | ID-based |
| Audio Formats | Multiple | Limited | Multiple |
| Error Handling | Comprehensive | Good | Good |

## References

- [Async.ai Documentation](https://docs.async.ai/text-to-speech-websocket-3477526w0)
- [Voicebot TTS Architecture](../src/voicebot/tts/)
- [WebSocket Provider Base](../src/voicebot/tts/websocket_provider.py)