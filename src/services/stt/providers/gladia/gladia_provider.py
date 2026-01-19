"""
Gladia STT Provider

WebSocket client for connecting to Gladia API for real-time
speech-to-text transcription.

Gladia uses a two-step process:
1. POST to /v2/live to initiate session and get WebSocket URL
2. Connect to WebSocket and send audio as binary frames
"""

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

import aiohttp

from services.provider_constants import get_provider_constants

logger = logging.getLogger(__name__)


class GladiaProvider:
    """
    STT provider that connects to Gladia API via WebSocket.
    """

    @classmethod
    def get_expected_properties(cls) -> list:
        """
        Get the list of expected properties for this provider.

        Returns:
            List of property names that this provider expects
        """
        return ["api_key"]

    @classmethod
    def get_field_definitions(cls) -> dict:
        """Get field definitions for Gladia STT provider."""
        return {
            "api_key": {
                "type": "password",
                "label": "API Key",
                "required": True,
                "description": "Gladia API key",
            },
            "language": {
                "type": "text",
                "label": "Language",
                "required": False,
                "description": "Language code (e.g., en, fr, sk). Leave empty for auto-detection.",
            },
            "model": {
                "type": "text",
                "label": "Model",
                "required": False,
                "description": "Model name (default: solaria-1)",
            },
        }

    def __init__(self, provider_config: dict = None):
        if provider_config:
            self.api_key = provider_config.get("api_key")
            self.language = provider_config.get("language")  # Can be None for auto-detect
            self.model = provider_config.get("model", "solaria-1")

            if not self.api_key:
                raise ValueError("API key is required for GladiaProvider")
        else:
            raise ValueError("Agent configuration is required for GladiaProvider")

        self.websocket = None
        self.session = None
        self.connected = False
        self.ws_url = None
        self.session_id = None
        self._transcript_queue = asyncio.Queue()

    async def _init_session(self) -> str:
        """
        Initialize a Gladia live session via POST request.
        
        Returns:
            WebSocket URL with token
        """
        constants = get_provider_constants()
        base_url = constants["stt"]["gladia.io"]["BASE_URL"]
        sample_rate = constants["stt"]["gladia.io"]["SAMPLE_RATE"]

        init_url = f"{base_url}/v2/live"
        
        headers = {
            "x-gladia-key": self.api_key,
            "Content-Type": "application/json",
        }

        # Build request body
        body = {
            "encoding": "wav/pcm",
            "bit_depth": 16,
            "sample_rate": sample_rate,
            "channels": 1,
            "model": self.model,
            "endpointing": 0.05,  # 50ms silence triggers utterance end
            "maximum_duration_without_endpointing": 5,
            "messages_config": {
                "receive_partial_transcripts": True,
                "receive_final_transcripts": True,
                "receive_speech_events": True,
                "receive_acknowledgments": False,
                "receive_errors": True,
                "receive_lifecycle_events": False,
            },
        }

        # Add language config if specified
        if self.language:
            body["language_config"] = {
                "languages": [self.language],
                "code_switching": False,
            }

        async with aiohttp.ClientSession() as session:
            async with session.post(init_url, headers=headers, json=body) as response:
                if response.status != 201:
                    error_text = await response.text()
                    raise ValueError(f"Failed to init Gladia session: {response.status} - {error_text}")
                
                data = await response.json()
                self.session_id = data.get("id")
                ws_url = data.get("url")
                logger.info(f"Gladia session initialized: {self.session_id}")
                return ws_url

    async def connect(self) -> None:
        """Connect to the Gladia WebSocket service."""
        try:
            # First, initialize session to get WebSocket URL
            self.ws_url = await self._init_session()
            
            # Connect to WebSocket
            self.session = aiohttp.ClientSession()
            self.websocket = await self.session.ws_connect(self.ws_url)
            self.connected = True
            
            logger.info(f"Connected to Gladia service, session: {self.session_id}")

        except Exception as e:
            logger.error(f"Failed to connect to Gladia service: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from the Gladia service."""
        if self.connected and self.websocket:
            try:
                # Send stop_recording message
                stop_message = json.dumps({"type": "stop_recording"})
                await self.websocket.send_str(stop_message)
                
                # Wait briefly for final transcripts
                await asyncio.sleep(0.5)
                
                await self.websocket.close()
                self.connected = False
                logger.info("Disconnected from Gladia service")
            except Exception as e:
                logger.error(f"Error disconnecting from Gladia service: {e}")

        if self.session:
            await self.session.close()
            self.session = None

    async def _receive_transcripts(self) -> None:
        """Receive and process transcripts from the WebSocket connection."""
        try:
            while self.connected and not self.websocket.closed:
                try:
                    message = await asyncio.wait_for(self.websocket.receive(), timeout=1.0)

                    if message.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(message.data)
                        transcript_data = self._parse_transcript(data)
                        if transcript_data:
                            await self._transcript_queue.put(transcript_data)
                    elif message.type == aiohttp.WSMsgType.ERROR:
                        logger.error(f"WebSocket error: {message.data}")
                        self.connected = False
                        break
                    elif message.type == aiohttp.WSMsgType.CLOSE:
                        logger.info("WebSocket connection closed")
                        self.connected = False
                        break

                except asyncio.TimeoutError:
                    continue

        except Exception as e:
            logger.error(f"Error receiving transcripts: {e}")
            self.connected = False

    def _parse_transcript(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse Gladia transcript into standardized format."""
        try:
            message_type = data.get("type")

            if message_type == "transcript":
                # Parse transcription results
                transcript_data = data.get("data", {})
                is_final = transcript_data.get("is_final", False)
                utterance = transcript_data.get("utterance", {})
                
                transcript_text = utterance.get("text", "").strip()
                if not transcript_text:
                    return None

                confidence = utterance.get("confidence", 0.0)
                language = utterance.get("language", "")

                return {
                    "transcript": transcript_text,
                    "is_final": is_final,
                    "confidence": confidence,
                    "stability": 1.0 if is_final else 0.5,
                    "provider": "gladia",
                    "model": self.model,
                    "language": language,
                }

            elif message_type == "speech_start":
                logger.debug("Speech started detected")
                return None

            elif message_type == "speech_end":
                logger.debug("Speech ended detected")
                return None

            elif message_type == "error":
                error_msg = data.get("error", "Unknown error")
                logger.error(f"Gladia error: {error_msg}")
                return None

            elif message_type in ("start_session", "start_recording", "end_recording", "end_session"):
                logger.debug(f"Gladia lifecycle event: {message_type}")
                return None

        except Exception as e:
            logger.error(f"Error parsing Gladia transcript: {e}")

        return None

    async def stream_audio_chunks(self, audio_chunk_generator: AsyncGenerator[bytes, None]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream individual audio chunks and receive real-time transcripts.

        Args:
            audio_chunk_generator: Async generator yielding audio chunks (16-bit PCM)

        Yields:
            Transcription results as dictionaries
        """
        if not self.connected:
            await self.connect()

        # Start receiving messages in background
        receive_task = asyncio.create_task(self._receive_transcripts())

        try:
            # Process audio chunks as they arrive
            async for audio_chunk in audio_chunk_generator:
                if audio_chunk and len(audio_chunk) > 0:
                    # Send audio chunk as binary frame (Gladia prefers this)
                    await self.websocket.send_bytes(audio_chunk)

                    # Yield any available transcripts from queue
                    while not self._transcript_queue.empty():
                        try:
                            transcript = await asyncio.wait_for(self._transcript_queue.get(), timeout=0.1)
                            yield transcript
                            self._transcript_queue.task_done()
                        except asyncio.TimeoutError:
                            break

            # Send stop_recording to flush remaining transcripts
            stop_message = json.dumps({"type": "stop_recording"})
            await self.websocket.send_str(stop_message)

            # Wait for final transcripts
            await asyncio.sleep(0.5)

            # Process any remaining transcripts
            while not self._transcript_queue.empty():
                try:
                    transcript = await asyncio.wait_for(self._transcript_queue.get(), timeout=0.1)
                    yield transcript
                    self._transcript_queue.task_done()
                except asyncio.TimeoutError:
                    break

        except Exception as e:
            logger.error(f"Error during audio chunk streaming: {e}")
            raise
        finally:
            # Cancel receive task and clean up
            receive_task.cancel()
            try:
                await receive_task
            except asyncio.CancelledError:
                pass

            if self.connected:
                await self.disconnect()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
