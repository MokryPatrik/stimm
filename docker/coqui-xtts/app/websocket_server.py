"""WebSocket server for Coqui XTTS streaming TTS."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import struct
from typing import Any, Dict, Optional

import websockets
from fastapi import WebSocket, WebSocketDisconnect

from main import (
    _load_tts_model,
    _split_text_segments,
    _audio_to_pcm16,
    _build_wav_stream_header,
    TTSRequest,
    LOGGER,
    DEFAULT_LANGUAGE,
    DEFAULT_SPEAKER,
    DEFAULT_REFERENCE_WAV,
    DEFAULT_STYLE_WAV,
)

# Configure logging for WebSocket server
WS_LOGGER = logging.getLogger("coqui_xtts_websocket")


class CoquiWebSocketServer:
    """WebSocket server for Coqui XTTS streaming TTS."""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 5001):
        self.host = host
        self.port = port
        self.active_connections: set[WebSocket] = set()
        
    async def handle_websocket(self, websocket: WebSocket):
        """Handle a WebSocket connection for TTS streaming."""
        await websocket.accept()
        self.active_connections.add(websocket)
        WS_LOGGER.info("WebSocket connection established from %s", websocket.client)
        
        try:
            # Wait for initialization message
            init_message = await websocket.receive_text()
            init_data = json.loads(init_message)
            
            if init_data.get("type") != "initialize":
                await websocket.send_json({
                    "type": "error",
                    "message": "First message must be 'initialize'"
                })
                return
                
            # Parse initialization parameters
            config = await self._parse_initialization(init_data)
            await websocket.send_json({"type": "initialized"})
            WS_LOGGER.info("WebSocket TTS session initialized: voice=%s, language=%s", 
                          config.voice_name, config.language_code)
            
            # Process text chunks
            async for message in websocket.iter_text():
                try:
                    data = json.loads(message)
                    if data.get("type") == "text_chunk":
                        await self._process_text_chunk(websocket, config, data)
                    elif data.get("type") == "close":
                        break
                except json.JSONDecodeError:
                    WS_LOGGER.warning("Invalid JSON message: %s", message)
                except Exception as exc:
                    WS_LOGGER.error("Error processing message: %s", exc)
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Processing error: {exc}"
                    })
                    
        except WebSocketDisconnect:
            WS_LOGGER.info("WebSocket disconnected")
        except Exception as exc:
            WS_LOGGER.error("WebSocket error: %s", exc)
        finally:
            self.active_connections.remove(websocket)
            
    async def _parse_initialization(self, init_data: Dict[str, Any]) -> TTSRequest:
        """Parse initialization message into TTS configuration."""
        # Create a base TTS request with defaults
        config = TTSRequest(
            text="",  # Will be set per chunk
            language=init_data.get("language_code", DEFAULT_LANGUAGE),
            speaker_id=init_data.get("voice_name", DEFAULT_SPEAKER),
            sample_rate=init_data.get("sample_rate_hz", 24000),
        )
        
        # Handle reference audio if provided
        if "reference_audio_b64" in init_data:
            config.reference_audio_b64 = init_data["reference_audio_b64"]
            
        return config
        
    async def _process_text_chunk(self, websocket: WebSocket, config: TTSRequest, data: Dict[str, Any]):
        """Process a text chunk and stream audio back."""
        text = data.get("text", "").strip()
        is_final = data.get("is_final", False)
        
        if not text:
            return
            
        WS_LOGGER.debug("Processing text chunk: %s (final=%s)", text[:50] + "..." if len(text) > 50 else text, is_final)
        
        # Update config with current text
        config.text = text
        
        try:
            # Use the existing rendering logic but adapt for WebSocket
            metadata, audio_stream = await self._render_tts_websocket(config)
            
            # Send audio header
            await websocket.send_json({
                "type": "audio_config",
                "sample_rate_hz": metadata.sample_rate,
                "language": metadata.language,
                "speaker_id": metadata.speaker_id,
            })
            
            # Stream audio chunks
            sequence = 0
            async for audio_chunk in audio_stream:
                if audio_chunk:
                    sequence += 1
                    # Encode audio as base64 for JSON transport
                    audio_b64 = base64.b64encode(audio_chunk).decode('utf-8')
                    
                    await websocket.send_json({
                        "type": "audio_chunk",
                        "data": audio_b64,
                        "sequence": sequence,
                        "sample_rate_hz": metadata.sample_rate,
                        "is_last": is_final and sequence > 0,  # Simple logic for last chunk
                    })
                    
            WS_LOGGER.debug("Sent %d audio chunks for text chunk", sequence)
            
        except Exception as exc:
            WS_LOGGER.error("Error processing TTS request: %s", exc)
            await websocket.send_json({
                "type": "error", 
                "message": f"TTS synthesis failed: {exc}"
            })
            
    async def _render_tts_websocket(self, request: TTSRequest):
        """Adapted version of _render_tts for WebSocket streaming."""
        from main import _tts_lock, TTSMetadata
        
        text = request.text.strip()
        if not text:
            raise ValueError("Text input cannot be empty")

        model = _load_tts_model()
        language = (request.language or DEFAULT_LANGUAGE or "en").strip()
        speaker_candidate = (
            request.speaker_id
            or request.speaker
            or DEFAULT_SPEAKER
        )
        speaker = speaker_candidate.strip() if speaker_candidate else None

        reference_path = None
        cleanup_reference = False
        if request.reference_audio_b64:
            # Decode base64 reference audio to temporary file
            import tempfile
            try:
                raw = base64.b64decode(request.reference_audio_b64)
                tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                tmp.write(raw)
                tmp.close()
                reference_path = tmp.name
                cleanup_reference = True
            except Exception as exc:
                WS_LOGGER.warning("Failed to decode reference audio: %s", exc)

        style_wav = None
        if DEFAULT_STYLE_WAV and os.path.exists(DEFAULT_STYLE_WAV):
            style_wav = DEFAULT_STYLE_WAV

        segments = _split_text_segments(text, max_chars=220, min_chars=80)
        sample_rate = getattr(model.synthesizer, "output_sample_rate", request.sample_rate or 24000)

        tts_kwargs = {"language": language, "split_sentences": False}
        if reference_path:
            tts_kwargs["speaker_wav"] = reference_path
        elif speaker:
            tts_kwargs["speaker"] = speaker
        if style_wav:
            tts_kwargs["style_wav"] = style_wav

        loop = asyncio.get_running_loop()

        async def _stream():
            async with _tts_lock:
                try:
                    # Don't send WAV header in WebSocket mode - let client handle it
                    for segment in segments:
                        segment = segment.strip()
                        if not segment:
                            continue

                        def _synth():
                            import torch
                            from TTS.api import TTS
                            
                            if (
                                torch is not None
                                and hasattr(model, 'synthesizer')
                                and torch.cuda.is_available()
                            ):
                                # Use appropriate device and dtype
                                device = getattr(model.synthesizer, 'device', 'cpu')
                                if device.type == 'cuda':
                                    with torch.autocast("cuda", dtype=torch.float16):
                                        return model.tts(text=segment, **tts_kwargs)
                            return model.tts(text=segment, **tts_kwargs)

                        audio_array = await loop.run_in_executor(None, _synth)
                        pcm_chunk = _audio_to_pcm16(audio_array)
                        if pcm_chunk:
                            yield pcm_chunk
                finally:
                    if cleanup_reference and reference_path:
                        import os
                        with contextlib.suppress(FileNotFoundError):
                            os.unlink(reference_path)

        metadata = TTSMetadata(sample_rate=sample_rate, language=language, speaker_id=speaker)
        return metadata, _stream()

    async def start(self):
        """Start the WebSocket server."""
        WS_LOGGER.info("Starting Coqui XTTS WebSocket server on %s:%s", self.host, self.port)
        async with websockets.serve(self.handle_websocket, self.host, self.port):
            await asyncio.Future()  # run forever


if __name__ == "__main__":
    import os
    import contextlib
    
    # Set up logging
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    
    # Start the WebSocket server
    server = CoquiWebSocketServer(host="0.0.0.0", port=5001)
    
    # Preload the TTS model
    WS_LOGGER.info("Preloading TTS model...")
    _load_tts_model()
    WS_LOGGER.info("TTS model loaded, starting WebSocket server")
    
    # Run the server
    asyncio.run(server.start())