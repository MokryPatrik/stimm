"""
Global provider-level constants.

This module freezes the global provider settings that were previously managed via:
- GlobalProviderConfig
- ProviderSettingTemplate
- DEFAULT_PROVIDER_TEMPLATES (deprecated, removed)
- /api/global-config and /agent/global-config (deprecated, removed)

Scope:
- ONLY truly global, shared, non-agent-specific defaults (URLs, paths, sample rates, encodings, etc.).
- NO agent-specific or secret values (api_key, voice_id, model_id, model, language, etc.).
- Stable across environments; if environment-specific behavior is needed, it should be handled
  at the provider/service level on top of these defaults.

Usage:
- Import from this module in provider implementations (LLM, TTS, STT) or services that need
  stable provider defaults, instead of any database-backed global configuration.
"""


# ======================================================================
# TTS PROVIDERS
# ======================================================================

class DeepgramTTSDefaults:
    """Global defaults for Deepgram TTS provider."""
    BASE_URL: str = "https://api.deepgram.com"
    SAMPLE_RATE: int = 16000
    ENCODING: str = "linear16"


class ElevenLabsTTSDefaults:
    """Global defaults for ElevenLabs TTS provider."""
    SAMPLE_RATE: int = 22050
    ENCODING: str = "pcm_s16le"
    OUTPUT_FORMAT: str = "pcm_22050"


class AsyncAITTSDefaults:
    """Global defaults for Async.AI TTS provider."""
    URL: str = "wss://api.async.ai/text_to_speech/websocket/ws"
    SAMPLE_RATE: int = 44100
    ENCODING: str = "pcm_s16le"
    CONTAINER: str = "raw"


class KokoroLocalTTSDefaults:
    """Global defaults for Kokoro Local TTS provider."""
    URL: str = "ws://kokoro-tts:5000/ws/tts/stream"
    SAMPLE_RATE: int = 33000
    ENCODING: str = "pcm_s16le"
    CONTAINER: str = "raw"
    SPEED: float = 0.8


# ======================================================================
# STT PROVIDERS
# ======================================================================

class DeepgramSTTDefaults:
    """Global defaults for Deepgram STT provider."""
    BASE_URL: str = "https://api.deepgram.com"
    SAMPLE_RATE: int = 16000


class WhisperLocalSTTDefaults:
    """Global defaults for Whisper Local STT provider."""
    URL: str = "ws://whisper-stt:8003"
    PATH: str = "/api/stt/stream"


# ======================================================================
# LLM PROVIDERS
# ======================================================================

class GroqLLMDefaults:
    """Global defaults for Groq LLM provider."""
    API_URL: str = "https://api.groq.com"
    COMPLETIONS_PATH: str = "/openai/v1/chat/completions"


class MistralLLMDefaults:
    """Global defaults for Mistral.ai LLM provider."""
    API_URL: str = "https://api.mistral.ai/v1"
    COMPLETIONS_PATH: str = "/chat/completions"


class OpenRouterLLMDefaults:
    """Global defaults for OpenRouter.ai LLM provider."""
    API_URL: str = "https://openrouter.ai/api/v1"
    COMPLETIONS_PATH: str = "/chat/completions"


class LlamaCppLLMDefaults:
    """Global defaults for llama-cpp.local LLM provider."""
    API_URL: str = "http://llama-cpp-server:8002"
    COMPLETIONS_PATH: str = "/v1/chat/completions"