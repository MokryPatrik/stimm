"""
Text-to-Speech Service Module with provider-based streaming support.
"""

import logging
from typing import AsyncGenerator, Optional, Dict, Any
from .config import tts_config
from .providers.async_ai.async_ai_provider import AsyncAIProvider
from .providers.kokoro_local.kokoro_local_provider import KokoroLocalProvider
from .providers.deepgram.deepgram_provider import DeepgramProvider
from .providers.elevenlabs.elevenlabs_provider import ElevenLabsProvider
from services.agent.agent_manager import get_agent_manager

logger = logging.getLogger(__name__)


class TTSService:
    """Service for handling Text-to-Speech operations"""

    def __init__(self, agent_id: Optional[str] = None, session_id: Optional[str] = None):
        self.agent_id = agent_id
        self.session_id = session_id
        self.provider = None
        self._initialize_provider()

    def _initialize_provider(self):
        # Use agent-based configuration if agent_id is provided
        if self.agent_id:
            agent_manager = get_agent_manager()
            agent_config = agent_manager.get_agent_config(self.agent_id)
            provider_name = agent_config.get("tts_provider")
            logger.info(f"Initializing TTS provider from agent {self.agent_id}: {provider_name}")
        else:
            # Fallback to environment-based configuration
            provider_name = tts_config.get_provider()
            logger.info(f"Initializing TTS provider from environment: {provider_name}")

        if provider_name == "async.ai":
            self.provider = AsyncAIProvider()
        elif provider_name == "kokoro.local":
            self.provider = KokoroLocalProvider()
        elif provider_name == "deepgram.com":
            self.provider = DeepgramProvider()
        elif provider_name == "elevenlabs.io":
            self.provider = ElevenLabsProvider()
        else:
            raise ValueError(f"Unsupported TTS provider: {provider_name}")
        
        logger.info(f"TTS provider initialized: {type(self.provider).__name__}")


    async def stream_synthesis(self, text_generator: AsyncGenerator[str, None]) -> AsyncGenerator[bytes, None]:
        """Stream synthesis using the configured provider."""
        if not self.provider:
            raise RuntimeError("TTS provider not initialized")

        # Delegate to the provider's stream_synthesis method
        async for audio_chunk in self.provider.stream_synthesis(text_generator):
            yield audio_chunk