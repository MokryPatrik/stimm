# Deepgram TTS Provider

This document describes the Deepgram TTS provider implementation for the voicebot application.

## Overview

The Deepgram TTS provider enables real-time text-to-speech synthesis using Deepgram's streaming WebSocket API. It provides high-quality, natural-sounding speech generation with support for multiple voice models and audio formats.

## Provider Structure

```
src/voicebot_app/services/tts/providers/deepgram/
├── __init__.py          # Package exports
├── deepgram_provider.py # Main provider implementation
└── test_deepgram_integration.py # Integration tests
```

## Key Components

1. **DeepgramProvider Class**: Main provider that implements the `stream_synthesis` method
2. **WebSocket Streaming**: Uses Deepgram's WebSocket protocol for real-time audio streaming
3. **Configuration**: Loads settings from environment variables via TTSConfig

## Configuration

### Environment Variables

```bash
# Core TTS provider selection
TTS_PROVIDER=deepgram.com

# Deepgram TTS API configuration
DEEPGRAM_TTS_API_KEY=your_deepgram_tts_api_key_here
DEEPGRAM_TTS_MODEL=aura-asteria-en
DEEPGRAM_TTS_SAMPLE_RATE=44100
DEEPGRAM_TTS_ENCODING=linear16
```

### Available Models

Deepgram provides multiple voice models:

- `aura-asteria-en` (default)
- `aura-luna-en`
- `aura-stella-en`
- `aura-athena-en`
- `aura-hera-en`
- `aura-orion-en`
- `aura-arcas-en`
- `aura-perseus-en`
- `aura-angus-en`
- `aura-orpheus-en`
- `aura-helios-en`
- `aura-zeus-en`

And many more Aura-2 models for different languages and voices.

### Audio Format Options

- **Sample Rates**: 8000, 16000, 24000, 44100, 48000 Hz
- **Encodings**: linear16, mulaw, alaw

## WebSocket Protocol

The provider implements Deepgram's TTS WebSocket protocol:

### Client Messages
- `SpeakV1Text`: Send text to convert to speech
- `SpeakV1Flush`: Flush buffer and receive final audio
- `SpeakV1Clear`: Clear buffer and start new generation
- `SpeakV1Close`: Close connection gracefully

### Server Messages
- `SpeakV1Audio`: Binary audio data (base64 encoded)
- `SpeakV1Metadata`: Generation metadata
- `SpeakV1Flushed`: Buffer flushed confirmation
- `SpeakV1Warning`: Warning messages
- `SpeakV1Cleared`: Buffer cleared confirmation

## TTS Service Integration

The provider is automatically loaded by the [`TTSService`](../src/voicebot_app/services/tts/tts.py) when `TTS_PROVIDER` is set to `"deepgram.com"`:

```python
def _initialize_provider(self):
    provider_name = self.config.get_provider()

    if provider_name == "async.ai":
        self.provider = AsyncAIProvider()
    elif provider_name == "kokoro.local":
        self.provider = KokoroLocalProvider()
    elif provider_name == "deepgram.com":
        self.provider = DeepgramProvider()
    else:
        raise ValueError(f"Unsupported TTS provider: {provider_name}")
```

## Usage Example

```python
from services.tts.tts import TTSService

# The provider is automatically selected based on TTS_PROVIDER
tts_service = TTSService()

async def text_generator():
    yield "Hello, "
    yield "this is a test "
    yield "of Deepgram TTS."

async for audio_chunk in tts_service.stream_synthesis(text_generator()):
    # Process audio chunks in real-time
    process_audio(audio_chunk)
```

## Testing

Run the integration test to verify the provider:

```bash
# Set your API key first
export DEEPGRAM_TTS_API_KEY=your_tts_api_key_here

# Run the test
python src/voicebot_app/services/tts/providers/deepgram/test_deepgram_integration.py
```

The test will:
1. Initialize the DeepgramProvider
2. Stream test text chunks
3. Receive and count audio chunks
4. Report success or failure

## Docker Integration

The Deepgram TTS provider works within the voicebot-app Docker container. The required dependencies are already included in the base image:

- `websockets` library for WebSocket connections
- `deepgram-sdk` (optional, not used in raw WebSocket implementation)

## Performance Characteristics

- **Latency**: Real-time streaming with minimal latency
- **Audio Quality**: High-quality neural voice synthesis
- **Format**: 44.1kHz, 16-bit linear PCM by default
- **Streaming**: Bidirectional WebSocket for continuous text input

## Error Handling

The provider includes comprehensive error handling for:
- WebSocket connection failures
- API authentication errors
- Network timeouts
- Invalid message formats
- Audio decoding errors

## References

- [Deepgram TTS Documentation](https://developers.deepgram.com/reference/text-to-speech/speak-streaming)
- [Voicebot TTS Architecture](../src/voicebot_app/services/tts/)
- [WebSocket Provider Pattern](../src/voicebot_app/services/tts/providers/)