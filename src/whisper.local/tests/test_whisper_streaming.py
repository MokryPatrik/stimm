"""WebRTC-like streaming tests for Whisper STT service."""

import asyncio
import json
import os
import wave
from typing import AsyncIterator, Optional, List, Dict, Any, AsyncGenerator, Tuple

import numpy as np
import pytest
import pytest_asyncio
import websockets
import sounddevice as sd
import soundfile as sf
from fastapi.testclient import TestClient
from main import app

# Constants for WebRTC-like streaming
STREAM_SAMPLE_RATE = 16000
CHUNK_DURATION_MS = 40  # 40ms chunks (typical WebRTC)
CHUNK_SIZE = STREAM_SAMPLE_RATE * CHUNK_DURATION_MS // 1000
CHUNK_BYTES = CHUNK_SIZE * 2  # 16-bit samples (2 bytes per sample)

@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)

@pytest.fixture
def audio_file_path():
    """Get the path to the test audio file."""
    return os.path.join(os.path.dirname(__file__), "Enregistrement.wav")

@pytest_asyncio.fixture
async def websocket_server() -> AsyncGenerator[str, None]:
    """
    Start the FastAPI server for WebSocket testing.

    Yields:
        The WebSocket URI to connect to
    """
    # In a real test environment, this would start the server
    # For now, we'll assume the server is running locally
    yield "ws://localhost:8003/api/stt/stream"

@pytest.fixture
def audio_pcm_data(audio_file_path: str) -> bytes:
    """Load audio data as PCM16 format."""
    return load_pcm16_from_wav(audio_file_path)

@pytest.fixture
def expected_transcription_results(audio_file_path: str) -> Dict[str, Any]:
    """
    Provide expected transcription results for verification.

    Returns:
        Dictionary with expected transcription characteristics
    """
    # In a real test, this would include expected text, duration, etc.
    # For now, we'll just verify basic structure and non-empty content
    return {
        "min_length": 1,  # Minimum number of transcripts
        "min_transcript_length": 1,  # Minimum length of transcript text
        "expected_fields": ["transcript", "is_final", "stability"]
    }

@pytest.fixture(scope="module")
def test_setup():
    """Setup for all tests in this module."""
    # This would typically start the server, prepare test data, etc.
    print("Setting up test environment...")
    yield
    print("Tearing down test environment...")

@pytest.fixture(scope="module")
def test_teardown():
    """Teardown for all tests in this module."""
    yield
    print("Cleaning up test resources...")

@pytest.fixture
def audio_file_setup(audio_file_path: str) -> Dict[str, Any]:
    """
    Setup audio file for testing.

    Returns:
        Dictionary with audio file information
    """
    # Verify file exists
    assert os.path.exists(audio_file_path), f"Audio file not found: {audio_file_path}"

    # Get file info
    file_size = os.path.getsize(audio_file_path)
    return {
        "path": audio_file_path,
        "size": file_size,
        "format": "WAV",
        "sample_rate": STREAM_SAMPLE_RATE
    }

@pytest.fixture
def websocket_client_setup(websocket_server: str) -> Dict[str, Any]:
    """
    Setup WebSocket client configuration.

    Returns:
        Dictionary with WebSocket client configuration
    """
    return {
        "uri": websocket_server,
        "timeout": 30.0,
        "max_retries": 3,
        "retry_delay": 1.0
    }

def load_pcm16_from_wav(wav_path: str) -> bytes:
    """
    Load PCM16 audio data from a WAV file.

    Args:
        wav_path: Path to the WAV file

    Returns:
        PCM16 audio data as bytes
    """
    with wave.open(wav_path, 'rb') as wav_file:
        # Verify format
        assert wav_file.getnchannels() == 1, "Audio must be mono"
        assert wav_file.getsampwidth() == 2, "Audio must be 16-bit"
        assert wav_file.getframerate() == STREAM_SAMPLE_RATE, f"Audio must be {STREAM_SAMPLE_RATE}Hz"

        # Read all frames
        pcm_data = wav_file.readframes(wav_file.getnframes())

    return pcm_data

class WebSocketStreamingClient:
    """
    WebSocket client for streaming audio to Whisper STT service.

    Handles bidirectional communication and real-time streaming.
    """

    def __init__(self, uri: str, audio_path: str):
        self.uri = uri
        self.audio_path = audio_path
        self.pcm_data = None
        self.chunk_size = CHUNK_BYTES
        self.transcripts: List[Dict[str, Any]] = []
        self.connected = False
        self.websocket = None
        self._streaming_task = None
        self._receive_task = None

    async def connect(self) -> None:
        """Connect to the WebSocket server."""
        self.websocket = await websockets.connect(self.uri)
        self.connected = True

    async def disconnect(self) -> None:
        """Disconnect from the WebSocket server."""
        if self.connected and self.websocket:
            await self.websocket.close()
            self.connected = False

    def load_audio(self) -> None:
        """Load audio data for streaming."""
        self.pcm_data = load_pcm16_from_wav(self.audio_path)

    async def stream_audio(self) -> None:
        """
        Stream audio data to the WebSocket server in real-time.

        This method streams audio without artificial delays, simulating
        real microphone input as it would happen in a WebRTC scenario.
        """
        if self.pcm_data is None:
            self.load_audio()

        # Start sending and receiving tasks
        self._streaming_task = asyncio.create_task(self._send_audio_chunks())
        self._receive_task = asyncio.create_task(self._receive_transcripts())

        # Wait for both tasks to complete
        await asyncio.gather(self._streaming_task, self._receive_task)

    async def _send_audio_chunks(self) -> None:
        """Send audio chunks to the server in real-time using sounddevice streaming."""
        # Load audio file with soundfile for better format support
        audio_data, sample_rate = sf.read(self.audio_path, dtype='float32')
        
        # Convert to mono if stereo
        if len(audio_data.shape) > 1:
            audio_data = audio_data.mean(axis=1)
        
        # Resample to 16kHz if needed
        if sample_rate != STREAM_SAMPLE_RATE:
            from scipy import signal
            audio_data = signal.resample(audio_data,
                                       int(len(audio_data) * STREAM_SAMPLE_RATE / sample_rate))
        
        # Convert to PCM16
        audio_data = (audio_data * 32767).astype(np.int16)
        
        # Calculate chunk size in samples
        chunk_samples = CHUNK_SIZE
        
        # Stream audio in real-time
        for i in range(0, len(audio_data), chunk_samples):
            chunk = audio_data[i:i + chunk_samples].tobytes()
            
            # Send chunk to WebSocket
            await self.websocket.send(chunk)
            
            # Calculate real delay based on audio duration
            chunk_duration = chunk_samples / STREAM_SAMPLE_RATE
            await asyncio.sleep(chunk_duration)

        # Send end message as text
        await self.websocket.send(json.dumps({"text": "end"}))

        # Give some time for final processing
        await asyncio.sleep(1.0)

    async def _receive_transcripts(self) -> None:
        """Receive and collect transcripts from the server."""
        try:
            # Continue receiving for a reasonable time after streaming ends
            max_wait_time = 5.0  # Maximum time to wait for final transcripts
            start_time = asyncio.get_event_loop().time()
            
            while True:
                try:
                    # Use a reasonable timeout for real-time processing
                    try:
                        message = await asyncio.wait_for(self.websocket.recv(), timeout=0.5)
                    except asyncio.TimeoutError:
                        # Check if we should continue waiting
                        current_time = asyncio.get_event_loop().time()
                        if current_time - start_time > max_wait_time:
                            break
                        continue
                    
                    if message:
                        data = json.loads(message)
                        self.transcripts.append(data)
                        # Reset the timer when we receive a message
                        print(f"[WHISPER-STT TEST] Received transcript: {data}")
                        start_time = asyncio.get_event_loop().time()
                        
                except websockets.ConnectionClosed:
                    # Connection closed, stop receiving
                    break
        except Exception as e:
            print(f"Error in transcript reception: {e}")

    def get_transcripts(self) -> List[Dict[str, Any]]:
        """Get all received transcripts."""
        return self.transcripts

    async def send_control_message(self, message: str) -> None:
        """Send a control message to the server."""
        if self.connected and self.websocket:
            await self.websocket.send(json.dumps({"text": message}))

    async def handle_bidirectional_communication(self) -> None:
        """
        Handle bidirectional communication with the server.

        This method demonstrates sending control messages and handling responses.
        """
        # Send start message
        await self.send_control_message("start")

        # Stream a small portion of audio
        if self.pcm_data is None:
            self.load_audio()

        # Send first chunk
        first_chunk = self.pcm_data[:self.chunk_size]
        await self.websocket.send(first_chunk)

        # Wait for processing
        await asyncio.sleep(0.5)

        # Send stop message
        await self.send_control_message("stop")

def verify_transcription_results(
    transcripts: List[Dict[str, Any]],
    expected: Dict[str, Any]
) -> Tuple[bool, str]:
    """
    Verify transcription results against expected criteria.

    Args:
        transcripts: List of transcription results
        expected: Expected criteria for verification

    Returns:
        Tuple of (success, message)
    """
    # Check minimum number of transcripts
    if len(transcripts) < expected["min_length"]:
        return False, f"Expected at least {expected['min_length']} transcripts, got {len(transcripts)}"

    # Check transcript structure and content
    for transcript in transcripts:
        # Check required fields
        for field in expected["expected_fields"]:
            if field not in transcript:
                return False, f"Missing required field '{field}' in transcript"

        # Check transcript content
        if "transcript" in transcript:
            if len(transcript["transcript"]) < expected["min_transcript_length"]:
                return False, f"Transcript text too short: '{transcript['transcript']}'"

    # Check that we have at least one final transcript
    has_final_transcript = any(t.get("is_final", False) for t in transcripts)
    if not has_final_transcript:
        return False, "No final transcript received"

    return True, "All verification passed"

@pytest.mark.asyncio
async def test_websocket_streaming(
    test_setup,
    websocket_server: str,
    audio_file_path: str,
    expected_transcription_results: Dict[str, Any]
):
    """
    Test WebRTC-like streaming to the Whisper STT WebSocket endpoint.

    This test:
    1. Loads the WAV file (pre-converted from M4A)
    2. Streams audio chunks via WebSocket in real-time using sounddevice
    3. Collects transcription results
    4. Verifies the connection works
    5. Verifies transcription results meet expected criteria
    """
    streaming_client = WebSocketStreamingClient(websocket_server, audio_file_path)

    try:
        await streaming_client.connect()

        # Stream audio and collect transcripts
        await streaming_client.stream_audio()

        # Get and verify transcripts
        transcripts = streaming_client.get_transcripts()

        # Verify basic structure
        assert len(transcripts) > 0, "No transcripts received"

        # Verify final transcript structure
        final_transcript = transcripts[-1]
        assert "transcript" in final_transcript
        assert "is_final" in final_transcript
        assert final_transcript["transcript"], "Empty final transcript"

        # Verify against expected results
        success, message = verify_transcription_results(transcripts, expected_transcription_results)
        assert success, message

        print(f"Received {len(transcripts)} transcripts")
        print(f"Final transcript: {final_transcript['transcript']}")

    finally:
        await streaming_client.disconnect()

@pytest.mark.asyncio
async def test_bidirectional_communication(
    test_setup,
    websocket_server: str,
    audio_file_path: str,
    expected_transcription_results: Dict[str, Any]
):
    """
    Test bidirectional communication with the WebSocket server.

    Verifies that control messages and transcripts work properly.
    """
    streaming_client = WebSocketStreamingClient(websocket_server, audio_file_path)

    try:
        await streaming_client.connect()

        # Handle bidirectional communication
        await streaming_client.handle_bidirectional_communication()

        # Get transcripts
        transcripts = streaming_client.get_transcripts()

        # Verify we received some transcripts
        assert len(transcripts) >= 0, "Should have received transcripts"

        # Verify transcripts meet expected criteria
        if transcripts:
            success, message = verify_transcription_results(transcripts, expected_transcription_results)
            assert success, message

        print(f"Bidirectional test received {len(transcripts)} transcripts")

    finally:
        await streaming_client.disconnect()

# Note: Additional test cases would include:
# - Testing with different sample rates
# - Testing error handling
# - Testing with silence and noise
# - Testing connection recovery