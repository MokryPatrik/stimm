"""WebSocket server for Kokoro TTS with seamless streaming support."""

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import numpy as np
from fastapi import WebSocket, WebSocketDisconnect
from kokoro_onnx import Kokoro

from .main import (
    DEFAULT_BLEND_RATIO,
    DEFAULT_LANGUAGE,
    DEFAULT_SAMPLE_RATE,
    DEFAULT_SPEED,
    DEFAULT_VOICE,
    PCM_SAMPLE_WIDTH_BYTES,
    PCM_CHANNELS,
    _audio_to_pcm16,
    _build_wav_stream_header,
    _clamp,
    _coerce_float,
    _load_model,
    _kokoro_model,
    _model_lock,
)

LOGGER = logging.getLogger("kokoro_websocket")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))


@dataclass
class WebSocketSynthesisContext:
    text: str
    language: str
    voice: str
    blend_with: Optional[str]
    blend_ratio: float
    speed: float
    requested_sample_rate: int


def _resolve_websocket_context(data: Dict[str, Any]) -> WebSocketSynthesisContext:
    """Parse WebSocket message data into synthesis context."""
    text = (data.get("text", "") or "").strip()
    if not text:
        raise ValueError("Text input cannot be empty")

    language = (data.get("language") or data.get("metadata", {}).get("language") or DEFAULT_LANGUAGE).strip()
    if not language:
        language = DEFAULT_LANGUAGE
    language = language.replace("_", "-").lower()

    voice = (data.get("voice") or data.get("speaker_id") or data.get("metadata", {}).get("voice") or DEFAULT_VOICE).strip()
    if not voice:
        raise ValueError("Voice not provided")

    blend_with = (data.get("blend_with") or data.get("metadata", {}).get("blend_with") or "").strip()
    if not blend_with:
        blend_with = None

    ratio_hint = data.get("blend_ratio")
    if ratio_hint is None and data.get("metadata"):
        ratio_hint = data.get("metadata", {}).get("blend_ratio")
    blend_ratio = _clamp(_coerce_float(ratio_hint, DEFAULT_BLEND_RATIO), 0.0, 1.0)

    speed = _coerce_float(data.get("speed") or data.get("metadata", {}).get("speed"), DEFAULT_SPEED)
    speed = _clamp(speed, 0.5, 2.0)

    requested_sample_rate = data.get("sample_rate") or data.get("metadata", {}).get("sample_rate") or DEFAULT_SAMPLE_RATE
    try:
        requested_sample_rate = int(requested_sample_rate)
    except (TypeError, ValueError):
        requested_sample_rate = DEFAULT_SAMPLE_RATE

    return WebSocketSynthesisContext(
        text=text,
        language=language,
        voice=voice,
        blend_with=blend_with,
        blend_ratio=blend_ratio,
        speed=speed,
        requested_sample_rate=requested_sample_rate,
    )


async def handle_websocket_connection(websocket: WebSocket):
    """Handle WebSocket connection for TTS streaming."""
    await websocket.accept()
    LOGGER.info("WebSocket connection established")
    
    try:
        # Load model if not already loaded
        model = await _load_model()
        
        while True:
            # Wait for TTS request
            data = await websocket.receive_json()
            LOGGER.info("Received TTS request: %s", data.get("text", "")[:50] + "...")
            
            try:
                # Parse request
                ctx = _resolve_websocket_context(data)
                
                # Prepare voice argument
                voice_argument: str | np.ndarray
                if ctx.blend_with:
                    try:
                        primary = model.get_voice_style(ctx.voice)
                    except KeyError as exc:
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Unknown voice '{ctx.voice}'"
                        })
                        continue
                    try:
                        secondary = model.get_voice_style(ctx.blend_with)
                    except KeyError as exc:
                        await websocket.send_json({
                            "type": "error", 
                            "message": f"Unknown blend voice '{ctx.blend_with}'"
                        })
                        continue
                    voice_argument = (primary * (1.0 - ctx.blend_ratio)) + (secondary * ctx.blend_ratio)
                else:
                    voice_argument = ctx.voice

                # Send start message
                await websocket.send_json({
                    "type": "start",
                    "sample_rate": DEFAULT_SAMPLE_RATE,
                    "language": ctx.language,
                    "voice": ctx.voice,
                    "blend_with": ctx.blend_with,
                    "blend_ratio": ctx.blend_ratio,
                    "speed": ctx.speed
                })

                # Stream audio chunks
                header_sent = False
                async for samples, sample_rate in model.create_stream(
                    ctx.text,
                    voice=voice_argument,
                    speed=ctx.speed,
                    lang=ctx.language,
                ):
                    if not header_sent:
                        # Send WAV header
                        header = _build_wav_stream_header(sample_rate)
                        await websocket.send_bytes(header)
                        header_sent = True
                    
                    # Send PCM audio chunk
                    chunk = _audio_to_pcm16(samples)
                    if chunk:
                        await websocket.send_bytes(chunk)

                # Send end message
                await websocket.send_json({
                    "type": "end",
                    "message": "TTS synthesis completed"
                })

            except ValueError as e:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
            except Exception as e:
                LOGGER.exception("Error during TTS synthesis")
                await websocket.send_json({
                    "type": "error",
                    "message": f"Synthesis error: {str(e)}"
                })
                
    except WebSocketDisconnect:
        LOGGER.info("WebSocket connection closed by client")
    except Exception as e:
        LOGGER.exception("WebSocket connection error")
        try:
            await websocket.close(code=1011, reason=str(e))
        except:
            pass


class KokoroWebSocketManager:
    """Manager for Kokoro WebSocket TTS connections."""
    
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """Accept connection and add to active connections."""
        await websocket.accept()
        self.active_connections.append(websocket)
        LOGGER.info("New WebSocket connection, total: %d", len(self.active_connections))
    
    def disconnect(self, websocket: WebSocket):
        """Remove connection from active connections."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        LOGGER.info("WebSocket disconnected, remaining: %d", len(self.active_connections))
    
    async def broadcast(self, message: str):
        """Broadcast message to all connected clients."""
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                self.disconnect(connection)


# Global WebSocket manager instance
websocket_manager = KokoroWebSocketManager()