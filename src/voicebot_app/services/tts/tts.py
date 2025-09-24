"""
Text-to-Speech Service Module with provider-based streaming support.
"""

import logging
from typing import AsyncGenerator
from .config import tts_config
from .providers.async_ai.async_ai_provider import AsyncAIProvider
from .providers.kokoro_local.kokoro_local_provider import KokoroLocalProvider

logger = logging.getLogger(__name__)


class TTSService:
    """Service for handling Text-to-Speech operations"""

    def __init__(self):
        self.config = tts_config
        self.provider = None
        self._initialize_provider()

    def _initialize_provider(self):
        provider_name = self.config.get_provider()
        logger.info(f"Initializing TTS provider: {provider_name}")

        if provider_name == "async.ai":
            self.provider = AsyncAIProvider()
        elif provider_name == "kokoro.local":
            self.provider = KokoroLocalProvider()
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