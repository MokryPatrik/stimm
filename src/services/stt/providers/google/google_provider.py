"""
Google Cloud Speech-to-Text Provider

Real-time streaming speech recognition using Google Cloud Speech-to-Text API v2.
Uses service account JSON credentials for authentication.
"""

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, Optional

from google.cloud.speech_v2 import SpeechAsyncClient
from google.cloud.speech_v2.types import cloud_speech
from google.oauth2 import service_account

from services.provider_constants import get_provider_constants

logger = logging.getLogger(__name__)


class GoogleSTTProvider:
    """
    STT provider that uses Google Cloud Speech-to-Text API v2 for real-time streaming.
    
    Authentication is via service account JSON credentials stored in the api_key field.
    """

    @classmethod
    def get_expected_properties(cls) -> list:
        """Get the list of expected properties for this provider."""
        return ["api_key"]

    @classmethod
    def get_field_definitions(cls) -> dict:
        """Get field definitions for Google STT provider."""
        return {
            "api_key": {
                "type": "textarea",
                "label": "Service Account JSON",
                "required": True,
                "description": "Google Cloud service account JSON credentials (paste the entire JSON content)",
            },
            "language": {
                "type": "text",
                "label": "Language",
                "required": False,
                "description": "Language code (e.g., en-US, sk-SK, fr-FR). Default: en-US",
            },
            "model": {
                "type": "text",
                "label": "Model",
                "required": False,
                "description": "Recognition model: 'long', 'short', 'telephony', 'chirp', 'chirp_2'. Default: long. Note: chirp models require location to be set.",
            },
            "location": {
                "type": "text",
                "label": "Location",
                "required": False,
                "description": "Google Cloud region (e.g., us-central1, europe-west1). Default: global. Required for chirp models.",
            },
        }

    def __init__(self, provider_config: dict = None):
        if not provider_config:
            raise ValueError("Provider configuration is required for GoogleSTTProvider")

        # Parse service account JSON from api_key field
        api_key_raw = provider_config.get("api_key")
        if not api_key_raw:
            raise ValueError("Service account JSON (api_key) is required for GoogleSTTProvider")

        # Parse the JSON credentials
        try:
            if isinstance(api_key_raw, str):
                self.credentials_info = json.loads(api_key_raw)
            else:
                self.credentials_info = api_key_raw
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid service account JSON: {e}")

        # Validate required fields in credentials
        required_fields = ["type", "project_id", "private_key", "client_email"]
        for field in required_fields:
            if field not in self.credentials_info:
                raise ValueError(f"Service account JSON missing required field: {field}")

        self.project_id = self.credentials_info["project_id"]
        self.language = provider_config.get("language", "en-US")
        self.model = provider_config.get("model", "long")
        
        # Location is required for chirp models, default to global for others
        self.location = provider_config.get("location", "")
        if not self.location:
            # Auto-detect location based on model
            if self.model and self.model.startswith("chirp"):
                self.location = "us-central1"  # Default for chirp models
            else:
                self.location = "global"

        # Get constants
        constants = get_provider_constants()
        self.sample_rate = constants["stt"]["google.cloud"]["SAMPLE_RATE"]

        # Initialize client (will be created on connect)
        self.client: Optional[SpeechAsyncClient] = None
        self.connected = False
        self._transcript_queue = asyncio.Queue()

    def _get_credentials(self) -> service_account.Credentials:
        """Create credentials from service account info."""
        return service_account.Credentials.from_service_account_info(
            self.credentials_info,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )

    async def connect(self) -> None:
        """Initialize the Google Speech client."""
        try:
            credentials = self._get_credentials()
            
            # Use location-specific endpoint for non-global locations
            if self.location and self.location != "global":
                api_endpoint = f"{self.location}-speech.googleapis.com"
                self.client = SpeechAsyncClient(
                    credentials=credentials,
                    client_options={"api_endpoint": api_endpoint}
                )
            else:
                self.client = SpeechAsyncClient(credentials=credentials)
            
            self.connected = True
            logger.info(f"Google STT client initialized for project: {self.project_id}, location: {self.location}, model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize Google STT client: {e}")
            raise

    async def disconnect(self) -> None:
        """Close the Google Speech client."""
        if self.client:
            # SpeechAsyncClient doesn't need explicit close, but we reset state
            self.client = None
            self.connected = False
            logger.info("Google STT client disconnected")

    def _get_streaming_config(self) -> cloud_speech.StreamingRecognitionConfig:
        """Build the streaming recognition configuration."""
        # Recognition config
        recognition_config = cloud_speech.RecognitionConfig(
            explicit_decoding_config=cloud_speech.ExplicitDecodingConfig(
                encoding=cloud_speech.ExplicitDecodingConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=self.sample_rate,
                audio_channel_count=1,
            ),
            language_codes=[self.language],
            model=self.model,
        )

        # Streaming config with interim results
        streaming_config = cloud_speech.StreamingRecognitionConfig(
            config=recognition_config,
            streaming_features=cloud_speech.StreamingRecognitionFeatures(
                interim_results=True,
                enable_voice_activity_events=True,
            ),
        )

        return streaming_config

    async def _audio_generator(
        self, 
        audio_chunk_generator: AsyncGenerator[bytes, None],
        streaming_config: cloud_speech.StreamingRecognitionConfig,
    ) -> AsyncGenerator[cloud_speech.StreamingRecognizeRequest, None]:
        """
        Generate streaming requests for Google Speech API.
        
        First request contains the config, subsequent requests contain audio.
        """
        # Recognizer resource name - use configured location
        recognizer = f"projects/{self.project_id}/locations/{self.location}/recognizers/_"

        # First request: config only
        yield cloud_speech.StreamingRecognizeRequest(
            recognizer=recognizer,
            streaming_config=streaming_config,
        )

        # Subsequent requests: audio content
        async for audio_chunk in audio_chunk_generator:
            if audio_chunk and len(audio_chunk) > 0:
                yield cloud_speech.StreamingRecognizeRequest(
                    audio=audio_chunk,
                )

    def _parse_response(self, response: cloud_speech.StreamingRecognizeResponse) -> Optional[Dict[str, Any]]:
        """Parse Google Speech response into standardized format."""
        try:
            # Check for speech events
            if response.speech_event_type:
                event_type = response.speech_event_type
                if event_type == cloud_speech.StreamingRecognizeResponse.SpeechEventType.SPEECH_ACTIVITY_BEGIN:
                    logger.debug("Speech activity started")
                    return None
                elif event_type == cloud_speech.StreamingRecognizeResponse.SpeechEventType.SPEECH_ACTIVITY_END:
                    logger.debug("Speech activity ended")
                    return None

            # Process recognition results
            if not response.results:
                return None

            for result in response.results:
                if not result.alternatives:
                    continue

                alternative = result.alternatives[0]
                transcript_text = alternative.transcript.strip()

                if not transcript_text:
                    continue

                is_final = result.is_final
                confidence = alternative.confidence if is_final else 0.0

                return {
                    "transcript": transcript_text,
                    "is_final": is_final,
                    "confidence": confidence,
                    "stability": result.stability if hasattr(result, 'stability') else (1.0 if is_final else 0.5),
                    "provider": "google",
                    "model": self.model,
                    "language": self.language,
                }

        except Exception as e:
            logger.error(f"Error parsing Google STT response: {e}")

        return None

    async def stream_audio_chunks(
        self, 
        audio_chunk_generator: AsyncGenerator[bytes, None]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream audio chunks and receive real-time transcripts.

        Args:
            audio_chunk_generator: Async generator yielding audio chunks (16-bit PCM, 16kHz mono)

        Yields:
            Transcription results as dictionaries
        """
        if not self.connected:
            await self.connect()

        try:
            streaming_config = self._get_streaming_config()
            
            # Create the audio request generator
            request_generator = self._audio_generator(audio_chunk_generator, streaming_config)

            # Stream to Google Speech API
            responses = await self.client.streaming_recognize(requests=request_generator)

            # Process responses
            async for response in responses:
                transcript_data = self._parse_response(response)
                if transcript_data:
                    yield transcript_data

        except Exception as e:
            logger.error(f"Error during Google STT streaming: {e}")
            raise
        finally:
            if self.connected:
                await self.disconnect()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
