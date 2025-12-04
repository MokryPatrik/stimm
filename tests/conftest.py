"""
Pytest configuration and shared fixtures for the test suite.

This module provides:
- Automatic .env file loading for test configuration
- Shared fixtures for audio files and test data
- Provider configuration fixtures
- Custom pytest markers for test categorization
- Automatic test skipping when required providers are unavailable
"""

import os
import sys
import wave
from pathlib import Path
from typing import Dict, Any, List

import pytest
import numpy as np
from dotenv import load_dotenv

# Load .env file from project root
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ Loaded test configuration from {env_file}")
else:
    print(f"⚠️ No .env file found at {env_file}, using system environment variables")

# Add src to Python path
sys.path.insert(0, str(project_root / "src"))


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests that don't require external dependencies"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests that may require external services"
    )
    config.addinivalue_line(
        "markers", "requires_provider(name): Tests that require a specific provider with API keys"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take a long time to run"
    )


def pytest_collection_modifyitems(config, items):
    """
    Automatically skip tests that require providers when API keys are missing.
    """
    for item in items:
        # Check for requires_provider marker
        marker = item.get_closest_marker("requires_provider")
        if marker:
            provider_type = marker.args[0] if marker.args else None
            if provider_type:
                # Check if required environment variables are present
                skip_reason = _check_provider_requirements(provider_type)
                if skip_reason:
                    item.add_marker(pytest.mark.skip(reason=skip_reason))


def _check_provider_requirements(provider_type: str) -> str | None:
    """
    Check if required environment variables for a provider are present.
    
    Args:
        provider_type: Type of provider (stt, tts, llm, etc.)
        
    Returns:
        Skip reason string if requirements not met, None otherwise
    """
    # Define required environment variables for each provider type
    requirements = {
        "stt": {
            "deepgram.com": ["DEEPGRAM_STT_API_KEY"],
            "whisper.local": [],  # Local service, no API key needed
        },
        "tts": {
            "async.ai": ["ASYNC_API_KEY"],
            "deepgram.com": ["DEEPGRAM_TTS_API_KEY"],
            "elevenlabs.io": ["ELEVENLABS_TTS_API_KEY"],
            "kokoro.local": [],  # Local service, no API key needed
        },
        "llm": {
            # LLM providers vary, check in the specific test
        },
    }
    
    if provider_type not in requirements:
        return None
    
    provider_reqs = requirements[provider_type]
    
    # For TTS, we consider at least one provider available if any API key is present
    # or if kokoro.local is configured (always). If none are available, skip.
    if provider_type == "tts":
        # Check each provider's required env vars
        any_available = False
        for provider_name, env_vars in provider_reqs.items():
            if not env_vars:
                # Local provider always considered available
                any_available = True
                break
            if all(os.getenv(var) for var in env_vars):
                any_available = True
                break
        if not any_available:
            return (
                "No TTS provider configuration found. "
                "Set at least one of: ASYNC_API_KEY, DEEPGRAM_TTS_API_KEY, ELEVENLABS_TTS_API_KEY "
                "or ensure kokoro.local service is running."
            )
        return None
    
    # For STT, we could implement similar logic, but currently rely on per-test skips
    # For now, keep placeholder behavior
    return None


# ============================================================================
# Audio Fixtures
# ============================================================================

@pytest.fixture
def audio_file_path() -> str:
    """Get the path to the standard test audio file."""
    audio_path = Path(__file__).parent / "resources" / "Enregistrement.wav"
    if not audio_path.exists():
        pytest.skip(f"Test audio file not found at {audio_path}")
    return str(audio_path)


@pytest.fixture
def audio_pcm_data(audio_file_path: str) -> bytes:
    """
    Load audio data as PCM16 format.
    
    Args:
        audio_file_path: Path to the WAV file
        
    Returns:
        PCM16 audio data as bytes
    """
    with wave.open(audio_file_path, 'rb') as wav_file:
        # Verify format
        assert wav_file.getnchannels() == 1, "Audio must be mono"
        assert wav_file.getsampwidth() == 2, "Audio must be 16-bit"
        assert wav_file.getframerate() == 16000, "Audio must be 16000Hz"
        
        # Read all frames
        pcm_data = wav_file.readframes(wav_file.getnframes())
    
    return pcm_data


@pytest.fixture
def silence_audio() -> bytes:
    """
    Generate 1 second of silence as PCM16 audio.
    
    Returns:
        PCM16 silence data as bytes
    """
    silence = np.zeros(16000, dtype=np.int16)
    return silence.tobytes()


# ============================================================================
# Provider Configuration Fixtures
# ============================================================================

@pytest.fixture
def deepgram_config() -> Dict[str, Any] | None:
    """
    Get Deepgram provider configuration from environment.
    
    Returns:
        Configuration dict or None if API key not available
    """
    api_key = os.getenv("DEEPGRAM_STT_API_KEY")
    if not api_key:
        return None
    
    return {
        "api_key": api_key,
        "model": os.getenv("DEEPGRAM_MODEL", "nova-2"),
        "language": os.getenv("DEEPGRAM_LANGUAGE", "fr"),
    }


@pytest.fixture
def whisper_config() -> Dict[str, Any]:
    """
    Get Whisper local provider configuration from environment.
    
    Returns:
        Configuration dict
    """
    # Prefer CUSTOM_WHISPER_STT_URL for consistency with provider constants
    url = os.getenv("CUSTOM_WHISPER_STT_URL") or os.getenv("WHISPER_LOCAL_STT_URL", "ws://whisper-stt:8003/api/stt/stream")
    return {
        "url": url
    }


@pytest.fixture
def async_ai_config() -> Dict[str, Any] | None:
    """
    Get Async.AI TTS provider configuration from environment.
    
    Returns:
        Configuration dict or None if API key not available
    """
    api_key = os.getenv("ASYNC_API_KEY")
    if not api_key:
        return None
    
    model = os.getenv("ASYNC_AI_TTS_MODEL_ID", "asyncflow_v2.0")
    return {
        "api_key": api_key,
        "voice": os.getenv("ASYNC_AI_TTS_VOICE_ID", "e7b694f8-d277-47ff-82bf-cb48e7662647"),
        "model": model,
        "model_id": model,  # provider expects model_id
    }


@pytest.fixture
def deepgram_tts_config() -> Dict[str, Any] | None:
    """
    Get Deepgram TTS provider configuration from environment.
    
    Returns:
        Configuration dict or None if API key not available
    """
    api_key = os.getenv("DEEPGRAM_TTS_API_KEY")
    if not api_key:
        return None
    
    return {
        "api_key": api_key,
        "model": os.getenv("DEEPGRAM_TTS_MODEL", "aura-asteria-en"),
    }


@pytest.fixture
def elevenlabs_config() -> Dict[str, Any] | None:
    """
    Get ElevenLabs TTS provider configuration from environment.
    
    Returns:
        Configuration dict or None if API key not available
    """
    api_key = os.getenv("ELEVENLABS_TTS_API_KEY")
    if not api_key:
        return None
    
    return {
        "api_key": api_key,
        "voice": os.getenv("ELEVENLABS_TTS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"),
        "model": os.getenv("ELEVENLABS_TTS_MODEL", "eleven_multilingual_v2"),
    }


@pytest.fixture
def kokoro_local_config() -> Dict[str, Any]:
    """
    Get Kokoro local TTS provider configuration from environment.
    
    Returns:
        Configuration dict (always available, uses defaults)
    """
    url = os.getenv("CUSTOM_KOKORO_TTS_URL") or os.getenv("KOKORO_LOCAL_TTS_URL", "ws://kokoro-tts:5000/ws/tts/stream")
    return {
        "voice": os.getenv("KOKORO_TTS_DEFAULT_VOICE", "af_sarah"),
        "language": os.getenv("KOKORO_TTS_DEFAULT_LANGUAGE", "fr-fr"),
        "url": url,
    }


@pytest.fixture
def available_stt_providers(deepgram_config, whisper_config) -> List[tuple[str, Dict[str, Any]]]:
    """
    Get list of available STT providers for parametrized testing.
    
    Returns:
        List of (provider_name, config) tuples for available providers
    """
    providers = []
    
    # Always include Whisper (local, no API key needed)
    providers.append(("whisper.local", whisper_config))
    
    # Include Deepgram only if API key is available
    if deepgram_config:
        providers.append(("deepgram.com", deepgram_config))
    
    return providers


@pytest.fixture
def stt_provider_ids(available_stt_providers) -> List[str]:
    """
    Get list of available STT provider IDs for pytest.mark.parametrize.
    
    Returns:
        List of provider names
    """
    return [name for name, _ in available_stt_providers]


@pytest.fixture
def available_tts_providers(
    async_ai_config,
    deepgram_tts_config,
    elevenlabs_config,
    kokoro_local_config,
) -> List[tuple[str, Dict[str, Any]]]:
    """
    Get list of available TTS providers for parametrized testing.
    
    Returns:
        List of (provider_name, config) tuples for available providers
    """
    providers = []
    
    # Always include Kokoro (local, no API key needed)
    providers.append(("kokoro.local", kokoro_local_config))
    
    # Include async.ai only if API key is available
    if async_ai_config:
        providers.append(("async.ai", async_ai_config))
    
    # Include deepgram.com only if API key is available
    if deepgram_tts_config:
        providers.append(("deepgram.com", deepgram_tts_config))
    
    # Include elevenlabs.io only if API key is available
    if elevenlabs_config:
        providers.append(("elevenlabs.io", elevenlabs_config))
    
    return providers


@pytest.fixture
def tts_provider_ids(available_tts_providers) -> List[str]:
    """
    Get list of available TTS provider IDs for pytest.mark.parametrize.
    
    Returns:
        List of provider names
    """
    return [name for name, _ in available_tts_providers]


# ============================================================================
# Expected Results Fixtures
# ============================================================================

@pytest.fixture
def expected_transcription_results() -> Dict[str, Any]:
    """
    Provide expected transcription results for verification.
    
    Returns:
        Dictionary with expected transcription characteristics
    """
    return {
        "min_length": 1,  # Minimum number of transcripts
        "min_transcript_length": 1,  # Minimum length of transcript text
        "expected_fields": ["transcript", "is_final"],
    }


# ============================================================================
# Test Constants
# ============================================================================

# Audio streaming constants (WebRTC-like)
STREAM_SAMPLE_RATE = 16000
CHUNK_DURATION_MS = 40  # 40ms chunks (typical WebRTC)
CHUNK_SIZE = STREAM_SAMPLE_RATE * CHUNK_DURATION_MS // 1000
CHUNK_BYTES = CHUNK_SIZE * 2  # 16-bit samples (2 bytes per sample)
