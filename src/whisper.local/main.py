"""FastAPI-based Whisper STT microservice with real-time streaming support."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import tempfile
import time
from dataclasses import dataclass
from typing import Optional

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from faster_whisper import WhisperModel

SUPPORTED_LANGUAGE_CODES = {
    "af",
    "am",
    "ar",
    "as",
    "az",
    "ba",
    "be",
    "bg",
    "bn",
    "bo",
    "br",
    "bs",
    "ca",
    "cs",
    "cy",
    "da",
    "de",
    "el",
    "en",
    "es",
    "et",
    "eu",
    "fa",
    "fi",
    "fo",
    "fr",
    "gl",
    "gu",
    "ha",
    "haw",
    "he",
    "hi",
    "hr",
    "ht",
    "hu",
    "hy",
    "id",
    "is",
    "it",
    "ja",
    "jw",
    "ka",
    "kk",
    "km",
    "kn",
    "ko",
    "la",
    "lb",
    "ln",
    "lo",
    "lt",
    "lv",
    "mg",
    "mi",
    "mk",
    "ml",
    "mn",
    "mr",
    "ms",
    "mt",
    "my",
    "ne",
    "nl",
    "nn",
    "no",
    "oc",
    "pa",
    "pl",
    "ps",
    "pt",
    "ro",
    "ru",
    "sa",
    "sd",
    "si",
    "sk",
    "sl",
    "sn",
    "so",
    "sq",
    "sr",
    "su",
    "sv",
    "sw",
    "ta",
    "te",
    "tg",
    "th",
    "tk",
    "tl",
    "tr",
    "tt",
    "uk",
    "ur",
    "uz",
    "vi",
    "yi",
    "yo",
    "zh",
    "yue",
}

LOGGER = logging.getLogger("whisper_stt_service")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

DEFAULT_MODEL_ID = os.getenv("WHISPER_MODEL_ID", "Systran/faster-whisper-medium")
DEFAULT_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
DEFAULT_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
STREAM_SAMPLE_RATE = int(os.getenv("WHISPER_STREAM_SAMPLE_RATE", "16000"))
STREAM_MIN_BUFFER_MS = int(os.getenv("WHISPER_STREAM_MIN_BUFFER_MS", "600"))
STREAM_UPDATE_MS = int(os.getenv("WHISPER_STREAM_UPDATE_MS", "400"))
STREAM_HISTORY_MS = int(os.getenv("WHISPER_STREAM_HISTORY_MS", "6000"))
STREAM_ENERGY_THRESHOLD = int(os.getenv("WHISPER_STREAM_ENERGY_THRESHOLD", "650"))
STREAM_MIN_SPEECH_MS = int(os.getenv("WHISPER_STREAM_MIN_SPEECH_MS", str(STREAM_MIN_BUFFER_MS)))
STREAM_SILENCE_MS = int(os.getenv("WHISPER_STREAM_SILENCE_MS", "800"))
STREAM_MAX_SEGMENT_MS = int(os.getenv("WHISPER_STREAM_MAX_SEGMENT_MS", str(STREAM_HISTORY_MS)))
STREAM_INTERIM_BEAM_SIZE = int(os.getenv("WHISPER_STREAM_INTERIM_BEAM_SIZE", "1"))
STREAM_FINAL_BEAM_SIZE = int(os.getenv("WHISPER_STREAM_FINAL_BEAM_SIZE", "3"))
STREAM_ENABLE_INTERIMS = os.getenv("WHISPER_STREAM_ENABLE_INTERIMS", "true").lower() not in {"0", "false", "no"}

_model: WhisperModel | None = None
_model_lock = asyncio.Lock()

app = FastAPI(
    title="Whisper Streaming STT",
    description="Standalone Whisper STT service with streaming WebSocket endpoint.",
    version="0.1.0",
)

async def _load_model() -> WhisperModel:
    global _model
    if _model is not None:
        return _model
    async with _model_lock:
        if _model is None:
            LOGGER.info(
                "Loading Whisper model id=%s device=%s compute_type=%s",
                DEFAULT_MODEL_ID,
                DEFAULT_DEVICE,
                DEFAULT_COMPUTE_TYPE,
            )
            loop = asyncio.get_running_loop()
            _model = await loop.run_in_executor(
                None,
                lambda: WhisperModel(
                    DEFAULT_MODEL_ID,
                    device=DEFAULT_DEVICE,
                    compute_type=DEFAULT_COMPUTE_TYPE,
                ),
            )
    return _model

def _pcm16_to_float32(pcm_bytes: bytes) -> np.ndarray:
    if not pcm_bytes:
        return np.zeros((0,), dtype=np.float32)
    audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
    return audio / 32768.0

async def _transcribe_array(
    model: WhisperModel,
    pcm_bytes: bytes,
    *,
    language: Optional[str],
    beam_size: int,
    vad_filter: bool,
) -> str:
    normalized_language = _normalize_language_code(language)
    if not pcm_bytes:
        return ""

    audio = _pcm16_to_float32(pcm_bytes)
    if audio.size == 0:
        return ""

    def _decode() -> str:
        segments, _info = model.transcribe(
            audio,
            language=normalized_language,
            beam_size=max(1, beam_size),
            temperature=0.0,
            vad_filter=vad_filter,
            condition_on_previous_text=False,
            compression_ratio_threshold=2.4,
            no_speech_threshold=0.6,
            word_timestamps=False,
            without_timestamps=True,
        )
        parts = [segment.text.strip() for segment in segments if segment.text]
        return " ".join(parts).strip()

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _decode)

async def _transcribe_file(path: str, *, language: Optional[str]) -> dict:
    model = await _load_model()
    normalized_language = _normalize_language_code(language)

    def _run() -> dict:
        segments, info = model.transcribe(
            path,
            language=normalized_language,
            beam_size=max(1, STREAM_FINAL_BEAM_SIZE),
            temperature=0.0,
            vad_filter=True,
            word_timestamps=False,
            without_timestamps=True,
        )
        transcript_parts = []
        payload_segments = []
        for segment in segments:
            text = (segment.text or "").strip()
            if not text:
                continue
            transcript_parts.append(text)
            payload_segments.append(
                {
                    "start": float(getattr(segment, "start", 0.0)),
                    "end": float(getattr(segment, "end", 0.0)),
                    "text": text,
                }
            )

        transcript = " ".join(transcript_parts).strip()
        return {
            "text": transcript,
            "language": getattr(info, "language", normalized_language or language),
            "duration": float(getattr(info, "duration", 0.0)),
            "segments": payload_segments,
        }

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _run)


def _normalize_language_code(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    lower = trimmed.replace("_", "-").lower()
    if lower == "auto":
        return None
    if lower in SUPPORTED_LANGUAGE_CODES:
        return lower
    primary = lower.split("-")[0]
    if primary in SUPPORTED_LANGUAGE_CODES:
        return primary
    return None

@dataclass(slots=True)
class StreamingConfig:
    """Runtime configuration for a streaming session."""

    sample_rate: int
    language: Optional[str]
    min_buffer_samples: int
    update_interval: float
    energy_threshold: int
    min_speech_ms: int
    silence_ms: int
    max_segment_ms: int
    history_samples: int
    interim_beam_size: int
    final_beam_size: int
    enable_interims: bool

class WhisperStreamingSession:
    """Manage incremental transcription for a WebSocket client."""

    def __init__(
        self,
        websocket: WebSocket,
        model: WhisperModel,
        config: StreamingConfig,
    ) -> None:
        self._websocket = websocket
        self._model = model
        self._config = config
        self._buffer = bytearray()
        self._segment_audio = bytearray()
        self._pending_chunks: list[bytes] = []
        self._last_transcript = ""
        self._active = True
        self._new_data = asyncio.Event()
        self._last_emit_ts = 0.0
        self._pending_final = False
        self._history_bytes = max(2, self._config.history_samples * 2)

        # Silence tracking
        self._segment_active = False
        self._speech_ms = 0.0
        self._silence_duration_ms = 0.0
        self._segment_ms = 0.0

    def append(self, chunk: bytes) -> None:
        if not self._active:
            return
        if not chunk:
            return
        if self._pending_final:
            self._pending_chunks.append(chunk)
            self._new_data.set()
            return

        self._segment_audio.extend(chunk)
        self._buffer.extend(chunk)
        if len(self._buffer) > self._history_bytes:
            del self._buffer[:-self._history_bytes]
        if self._should_finalize(chunk):
            self._pending_final = True
        self._new_data.set()

    def stop(self) -> None:
        self._active = False
        self._new_data.set()

    def _reset_silence_state(self) -> None:
        self._segment_active = False
        self._speech_ms = 0.0
        self._silence_duration_ms = 0.0
        self._segment_ms = 0.0

    def _should_finalize(self, chunk: bytes) -> bool:
        samples = len(chunk) // 2
        if samples <= 0:
            return False
        chunk_ms = (samples / self._config.sample_rate) * 1000.0
        pcm = np.frombuffer(chunk, dtype=np.int16)
        peak = int(np.abs(pcm).max()) if pcm.size else 0
        is_active = peak >= self._config.energy_threshold

        if is_active:
            self._segment_active = True
            self._speech_ms += chunk_ms
            self._segment_ms += chunk_ms
            self._silence_duration_ms = 0.0
        else:
            if self._segment_active:
                self._silence_duration_ms += chunk_ms
                self._segment_ms += chunk_ms
            else:
                self._segment_ms = 0.0

        should_flush = (
            self._segment_active
            and self._speech_ms >= self._config.min_speech_ms
            and (
                self._silence_duration_ms >= self._config.silence_ms
                or self._segment_ms >= self._config.max_segment_ms
            )
        )

        if should_flush:
            self._reset_silence_state()

        return should_flush

    async def _emit_transcript(self, transcript: str, *, is_final: bool) -> None:
        payload = {
            "transcript": transcript,
            "is_final": is_final,
            "stability": 1.0 if is_final else 0.6,
        }
        try:
            await self._websocket.send_json(payload)
        except (RuntimeError, WebSocketDisconnect):
            LOGGER.debug("WebSocket send skipped; channel already closed")

    async def _maybe_transcribe(self, *, is_final: bool = False, audio_bytes: Optional[bytes] = None) -> None:
        payload = audio_bytes if audio_bytes is not None else bytes(self._buffer)
        if not payload:
            if is_final and self._last_transcript:
                await self._emit_transcript(self._last_transcript, is_final=True)
            elif is_final:
                await self._emit_transcript("", is_final=True)
            return

        transcript = await _transcribe_array(
            self._model,
            payload,
            language=self._config.language,
            beam_size=self._config.final_beam_size if is_final else self._config.interim_beam_size,
            vad_filter=False,
        )
        transcript = transcript.strip()
        if not transcript:
            if is_final:
                await self._emit_transcript("", is_final=True)
            return

        if transcript == self._last_transcript and not is_final:
            return

        self._last_transcript = transcript
        await self._emit_transcript(transcript, is_final=is_final)

    async def _finalize_segment(self) -> None:
        segment_bytes = bytes(self._segment_audio)
        await self._maybe_transcribe(is_final=True, audio_bytes=segment_bytes)
        self._buffer.clear()
        self._segment_audio.clear()
        self._last_transcript = ""
        self._pending_final = False
        self._reset_silence_state()

        self._merge_pending_chunks()

    def _merge_pending_chunks(self) -> None:
        if not self._pending_chunks:
            return

        remaining: list[bytes] = []
        for chunk in self._pending_chunks:
            if self._pending_final:
                remaining.append(chunk)
                continue
            self._segment_audio.extend(chunk)
            self._buffer.extend(chunk)
            if len(self._buffer) > self._history_bytes:
                del self._buffer[:-self._history_bytes]
            if self._should_finalize(chunk):
                self._pending_final = True
        self._pending_chunks = remaining

        if self._pending_final or self._buffer:
            self._new_data.set()

    async def run(self) -> None:
        min_samples = max(1, self._config.min_buffer_samples)
        update_interval = max(0.05, self._config.update_interval)

        try:
            while self._active:
                await self._new_data.wait()
                self._new_data.clear()

                if self._pending_final:
                    await self._finalize_segment()
                    continue

                num_samples = len(self._buffer) // 2
                if num_samples < min_samples:
                    continue

                if not self._config.enable_interims:
                    continue

                now = time.monotonic()
                elapsed = now - self._last_emit_ts
                if elapsed < update_interval:
                    await asyncio.sleep(update_interval - elapsed)

                await self._maybe_transcribe()
                self._last_emit_ts = time.monotonic()

            # Connection closing: flush remaining audio.
            while self._pending_final:
                await self._finalize_segment()

            if self._pending_chunks:
                for pending in self._pending_chunks:
                    self._segment_audio.extend(pending)
                    self._buffer.extend(pending)
                self._pending_chunks.clear()

            if self._segment_audio:
                await self._maybe_transcribe(is_final=True, audio_bytes=bytes(self._segment_audio))
                self._segment_audio.clear()
        except Exception as exc:
            LOGGER.exception("Streaming session failed")
            await self._websocket.send_json(
                {
                    "transcript": "",
                    "is_final": True,
                    "stability": 0.0,
                    "error": str(exc),
                }
            )

@app.websocket("/api/stt/stream")
async def stt_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    params = websocket.query_params
    sample_rate = int(params.get("sample_rate", STREAM_SAMPLE_RATE))
    language = _normalize_language_code(params.get("language") or params.get("language_code"))
    min_buffer_ms = max(200, STREAM_MIN_BUFFER_MS)
    update_ms = max(120, STREAM_UPDATE_MS)

    min_samples = sample_rate * min_buffer_ms // 1000
    min_speech_ms = max(200, STREAM_MIN_SPEECH_MS)
    silence_ms = max(200, STREAM_SILENCE_MS)
    max_segment_ms = max(STREAM_MAX_SEGMENT_MS, min_buffer_ms * 4, min_speech_ms)
    history_ms = max(STREAM_HISTORY_MS, min_buffer_ms * 3)
    history_samples = sample_rate * history_ms // 1000
    config = StreamingConfig(
        sample_rate=sample_rate,
        language=language,
        min_buffer_samples=min_samples,
        update_interval=update_ms / 1000.0,
        energy_threshold=max(1, STREAM_ENERGY_THRESHOLD),
        min_speech_ms=min_speech_ms,
        silence_ms=silence_ms,
        max_segment_ms=max_segment_ms,
        history_samples=history_samples,
        interim_beam_size=max(1, STREAM_INTERIM_BEAM_SIZE),
        final_beam_size=max(1, STREAM_FINAL_BEAM_SIZE),
        enable_interims=STREAM_ENABLE_INTERIMS,
    )

    model = await _load_model()
    session = WhisperStreamingSession(websocket, model, config)
    runner = asyncio.create_task(session.run())

    try:
        while True:
            message = await websocket.receive()
            if "bytes" in message:
                session.append(message["bytes"])
            elif "text" in message:
                text = (message["text"] or "").strip().lower()
                if text in {"close", "stop", "end"}:
                    break
            elif message.get("type") == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        LOGGER.info("WebSocket disconnected")
    finally:
        session.stop()
        with contextlib.suppress(asyncio.CancelledError):
            await runner
        with contextlib.suppress(RuntimeError):
            await websocket.close()