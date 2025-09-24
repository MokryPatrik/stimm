"""FastAPI service exposing Coqui XTTS v2 (TTS) endpoints."""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import struct
import tempfile
from typing import Any, AsyncGenerator, Dict, List, Optional
import contextlib
import re

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict

from TTS.api import TTS

try:
    import torch
except Exception:  # pragma: no cover - optional GPU availability
    torch = None

try:
    from TTS.utils import manage as tts_manage
except ImportError:  # pragma: no cover - defensive
    tts_manage = None
else:
    def _accept_tos(self, output_path: str) -> bool:  # type: ignore[override]
        return True

    if hasattr(tts_manage, "ModelManager") and hasattr(tts_manage.ModelManager, "ask_tos"):
        tts_manage.ModelManager.ask_tos = _accept_tos  # type: ignore[assignment]

LOGGER = logging.getLogger("coqui_xtts_service")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

DEFAULT_LANGUAGE = os.getenv("COQUI_TTS_DEFAULT_LANGUAGE", "fr")
DEFAULT_SPEAKER = (os.getenv("COQUI_TTS_DEFAULT_SPEAKER") or None)
DEFAULT_TTS_MODEL_ID = os.getenv("COQUI_TTS_MODEL_ID", "tts_models/multilingual/multi-dataset/xtts_v2")
DEFAULT_TTS_DEVICE = os.getenv("COQUI_TTS_DEVICE", "cpu")
DEFAULT_TTS_DTYPE = os.getenv("COQUI_TTS_DTYPE", "").lower()
DEFAULT_REFERENCE_WAV = os.getenv("COQUI_TTS_REFERENCE_WAV")
DEFAULT_STYLE_WAV = os.getenv("COQUI_TTS_STYLE_WAV")
SEGMENT_MAX_CHARS = max(40, int(os.getenv("COQUI_TTS_SEGMENT_MAX_CHARS", "220")))
SEGMENT_MIN_CHARS = max(10, int(os.getenv("COQUI_TTS_SEGMENT_MIN_CHARS", "80")))
if SEGMENT_MIN_CHARS > SEGMENT_MAX_CHARS:
    SEGMENT_MIN_CHARS = max(10, SEGMENT_MAX_CHARS // 2)

HF_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
if HF_TOKEN and "HF_AUTH_TOKEN" not in os.environ:
    os.environ["HF_AUTH_TOKEN"] = HF_TOKEN

os.environ.setdefault("COQUI_TOS_ACCEPTED", "1")

_tts_model: Optional[TTS] = None
_tts_lock = asyncio.Lock()
_gpu_logged = False

app = FastAPI(
    title="Coqui XTTS Speech Service",
    description="REST endpoints for XTTS v2 speech synthesis and Whisper-based ASR.",
    version="0.1.0",
)


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


_ensure_dir(os.environ.get("COQUI_CACHE_DIR", "/models/cache"))
_ensure_dir(os.environ.get("HF_HOME", "/models/huggingface"))
_ensure_dir(os.environ.get("TTS_HOME", "/models/tts"))


def _load_tts_model() -> TTS:
    global _tts_model, DEFAULT_SPEAKER, DEFAULT_TTS_DEVICE, _gpu_logged
    if _tts_model is not None:
        return _tts_model

    LOGGER.info(
        "Loading Coqui XTTS model id=%s device=%s",
        DEFAULT_TTS_MODEL_ID,
        DEFAULT_TTS_DEVICE,
    )
    model = TTS(model_name=DEFAULT_TTS_MODEL_ID, progress_bar=False)
    if DEFAULT_TTS_DEVICE and DEFAULT_TTS_DEVICE != "auto":
        target_device = DEFAULT_TTS_DEVICE
        try:
            model.to(target_device)
        except Exception as exc:  # pragma: no cover - hardware dependent
            LOGGER.warning(
                "Unable to move TTS model to %s (%s); falling back to CPU",
                target_device,
                exc,
            )
            target_device = "cpu"
            DEFAULT_TTS_DEVICE = target_device
            model.to(target_device)

    if torch is not None and not _gpu_logged:
        if torch.cuda.is_available():
            index = torch.cuda.current_device()
            device_name = torch.cuda.get_device_name(index)
            LOGGER.info("CUDA available: True device=%s", device_name)
        else:
            LOGGER.warning("CUDA available: False - running on CPU")
        _gpu_logged = True

    if DEFAULT_SPEAKER is None:
        try:
            DEFAULT_SPEAKER_LIST = getattr(model, "speakers", None)
            if DEFAULT_SPEAKER_LIST:
                speaker = DEFAULT_SPEAKER_LIST[0]
                LOGGER.info("Default speaker not set; using first available speaker=%s", speaker)
                os.environ["COQUI_TTS_DEFAULT_SPEAKER"] = speaker
                DEFAULT_SPEAKER = speaker
        except Exception as exc:  # pragma: no cover - defensive
            LOGGER.warning("Unable to discover default speaker: %s", exc)
    if DEFAULT_SPEAKER is None:
        LOGGER.warning(
            "XTTS bundle does not provide predefined speakers. Configure COQUI_TTS_DEFAULT_SPEAKER or supply a reference wav."
        )
    _tts_model = model
    return model


PCM_SAMPLE_WIDTH_BYTES = 2
PCM_CHANNELS = 1


def _build_wav_stream_header(sample_rate: int) -> bytes:
    bits_per_sample = PCM_SAMPLE_WIDTH_BYTES * 8
    byte_rate = sample_rate * PCM_CHANNELS * PCM_SAMPLE_WIDTH_BYTES
    block_align = PCM_CHANNELS * PCM_SAMPLE_WIDTH_BYTES
    return struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        0xFFFFFFFF,
        b"WAVE",
        b"fmt ",
        16,
        1,
        PCM_CHANNELS,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        0xFFFFFFFF,
    )


def _audio_to_pcm16(audio: np.ndarray) -> bytes:
    data = np.asarray(audio, dtype=np.float32)
    if data.size == 0:
        return b""
    clipped = np.clip(data, -1.0, 1.0)
    pcm = (clipped * 32767.0).astype("<i2")
    return pcm.tobytes()


def _split_text_segments(text: str, *, max_chars: int, min_chars: int) -> List[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    segments: List[str] = []
    buffer = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        candidate = f"{buffer} {sentence}".strip() if buffer else sentence
        if len(candidate) <= max_chars:
            buffer = candidate
        else:
            if buffer:
                segments.append(buffer)
            if len(sentence) <= max_chars:
                buffer = sentence
            else:
                start = 0
                while start < len(sentence):
                    end = min(len(sentence), start + max_chars)
                    chunk = sentence[start:end].strip()
                    if chunk:
                        segments.append(chunk)
                    start = end
                buffer = ""
    if buffer:
        segments.append(buffer)

    # Merge tiny tail segments
    normalized: List[str] = []
    for segment in segments:
        if normalized and len(segment) < min_chars:
            normalized[-1] = f"{normalized[-1]} {segment}".strip()
        else:
            normalized.append(segment)
    return normalized or [text.strip()]


class TTSRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: str
    language: Optional[str] = None
    speaker_id: Optional[str] = None
    speaker: Optional[str] = None
    sample_rate: Optional[int] = None
    reference_audio_b64: Optional[str] = None


class TTSMetadata(BaseModel):
    sample_rate: int
    language: str
    speaker_id: Optional[str] = None


def _decode_reference_audio(reference_b64: str) -> Tuple[str, str]:
    """Persist base64 encoded reference audio to a temporary wav file."""
    try:
        raw = base64.b64decode(reference_b64)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid base64 reference audio: {exc}") from exc

    suffix = ".wav"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.write(raw)
    tmp.flush()
    tmp.close()
    return tmp.name, suffix


async def _render_tts(request: TTSRequest) -> Tuple[TTSMetadata, AsyncGenerator[bytes, None]]:
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text input cannot be empty")

    model = _load_tts_model()
    language = (request.language or DEFAULT_LANGUAGE or "en").strip()
    speaker_candidate = (
        request.speaker_id
        or request.speaker
        or os.getenv("COQUI_TTS_DEFAULT_SPEAKER")
        or DEFAULT_SPEAKER
    )
    speaker = speaker_candidate.strip() if speaker_candidate else None

    reference_path: Optional[str] = None
    cleanup_reference = False
    if request.reference_audio_b64:
        reference_path, _ = _decode_reference_audio(request.reference_audio_b64)
        cleanup_reference = True
    elif DEFAULT_REFERENCE_WAV:
        if os.path.exists(DEFAULT_REFERENCE_WAV):
            reference_path = DEFAULT_REFERENCE_WAV
        else:
            LOGGER.warning(
                "Configured COQUI_TTS_REFERENCE_WAV=%s does not exist; ignoring.",
                DEFAULT_REFERENCE_WAV,
            )

    style_wav = None
    if DEFAULT_STYLE_WAV:
        if os.path.exists(DEFAULT_STYLE_WAV):
            style_wav = DEFAULT_STYLE_WAV
        else:
            LOGGER.warning(
                "Configured COQUI_TTS_STYLE_WAV=%s does not exist; ignoring.",
                DEFAULT_STYLE_WAV,
            )

    segments = _split_text_segments(text, max_chars=SEGMENT_MAX_CHARS, min_chars=SEGMENT_MIN_CHARS)
    sample_rate = getattr(model.synthesizer, "output_sample_rate", request.sample_rate or 24000)
    if request.sample_rate and request.sample_rate != sample_rate:
        LOGGER.warning(
            "Requested sample rate %d differs from XTTS output %d; returning native sample rate.",
            request.sample_rate,
            sample_rate,
        )

    tts_kwargs: Dict[str, Any] = {"language": language, "split_sentences": False}
    if reference_path:
        tts_kwargs["speaker_wav"] = reference_path
    elif speaker:
        tts_kwargs["speaker"] = speaker
    if style_wav:
        tts_kwargs["style_wav"] = style_wav

    loop = asyncio.get_running_loop()

    async def _stream() -> AsyncGenerator[bytes, None]:
        async with _tts_lock:
            try:
                yield _build_wav_stream_header(sample_rate)
                for segment in segments:
                    segment = segment.strip()
                    if not segment:
                        continue

                    def _synth() -> np.ndarray:
                        if (
                            torch is not None
                            and DEFAULT_TTS_DEVICE.startswith("cuda")
                            and torch.cuda.is_available()
                            and DEFAULT_TTS_DTYPE in {"float16", "fp16"}
                        ):
                            with torch.autocast("cuda", dtype=torch.float16):
                                return model.tts(text=segment, **tts_kwargs)
                        return model.tts(text=segment, **tts_kwargs)

                    audio_array: np.ndarray = await loop.run_in_executor(None, _synth)
                    pcm_chunk = _audio_to_pcm16(audio_array)
                    if pcm_chunk:
                        yield pcm_chunk
            finally:
                if cleanup_reference and reference_path:
                    with contextlib.suppress(FileNotFoundError):
                        os.unlink(reference_path)

    metadata = TTSMetadata(sample_rate=sample_rate, language=language, speaker_id=speaker)
    return metadata, _stream()


@app.get("/healthz")
async def healthz() -> JSONResponse:
    status = {
        "tts_model": DEFAULT_TTS_MODEL_ID,
        "tts_device": DEFAULT_TTS_DEVICE,
    }
    return JSONResponse(status)


@app.post("/api/tts")
async def synthesize(request: TTSRequest) -> StreamingResponse:
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text input cannot be empty")

    metadata, stream = await _render_tts(request)

    headers = {
        "X-Sample-Rate": str(metadata.sample_rate),
        "X-Voice-Language": metadata.language,
    }
    if metadata.speaker_id:
        headers["X-Speaker-Id"] = metadata.speaker_id
