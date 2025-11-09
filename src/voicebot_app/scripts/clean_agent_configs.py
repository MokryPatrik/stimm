"""
One-off script to normalize agent provider configs in the database.

Run this INSIDE the voicebot-app container, e.g.:

    docker compose exec voicebot-app python -m scripts.clean_agent_configs

What it does (non-destructive):
- Ensures standardized fields exist based on legacy provider-specific keys.
- Does NOT drop legacy keys (voice_id/model_id) in this pass to avoid surprises.
- Can be safely re-run.

Standardization rules:
- LLM (all providers):
    - Keep existing "model" and "api_key" as-is (already standardized).

- TTS:
    - For elevenlabs.io:
        - if voice missing and voice_id present -> voice = voice_id
        - if model missing and model_id present -> model = model_id
    - For async.ai:
        - if voice missing and voice_id present -> voice = voice_id
        - if model missing and model_id present -> model = model_id or "tts-1"
    - For kokoro.local:
        - if voice missing and voice_id present -> voice = voice_id
    - Deepgram and others:
        - leave as-is; they already use model/voice consistently.

- STT:
    - Ensure "model" and "api_key" keys exist if legacy variants were used in the future.

After verifying behavior in staging, you may implement a second pass
to remove redundant legacy keys.
"""

import logging
from typing import Dict, Any

from database.session import SessionLocal
from database.models import Agent

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def _normalize_elevenlabs_tts(config: Dict[str, Any]) -> Dict[str, Any]:
    # Prefer standardized keys; if missing, backfill from legacy keys.
    voice = config.get("voice")
    voice_id = config.get("voice_id")
    if not voice and voice_id:
        config["voice"] = voice_id

    model = config.get("model")
    model_id = config.get("model_id")
    if not model and model_id:
        config["model"] = model_id

    return config


def _normalize_async_ai_tts(config: Dict[str, Any]) -> Dict[str, Any]:
    # Backfill standardized fields from voice_id/model_id if missing.
    voice = config.get("voice")
    voice_id = config.get("voice_id")
    if not voice and voice_id:
        config["voice"] = voice_id

    model = config.get("model")
    model_id = config.get("model_id")
    if not model and model_id:
        config["model"] = model_id
    if not config.get("model") and not model_id:
        # Keep existing behavior: async.ai expects a model; default used in provider.
        config["model"] = "tts-1"

    return config


def _normalize_kokoro_tts(config: Dict[str, Any]) -> Dict[str, Any]:
    # Historically used voice_id; prefer standardized voice.
    voice = config.get("voice")
    voice_id = config.get("voice_id")
    if not voice and voice_id:
        config["voice"] = voice_id
    return config


def _normalize_agent(agent: Agent) -> bool:
    """
    Normalize a single Agent's configs.
    Returns True if any changes were made.
    """
    changed = False

    # Normalize TTS config
    tts = dict(agent.tts_config or {})
    provider = agent.tts_provider

    if provider == "elevenlabs.io":
        before = dict(tts)
        tts = _normalize_elevenlabs_tts(tts)
        if tts != before:
            changed = True

    elif provider == "async.ai":
        before = dict(tts)
        tts = _normalize_async_ai_tts(tts)
        if tts != before:
            changed = True

    elif provider == "kokoro.local":
        before = dict(tts)
        tts = _normalize_kokoro_tts(tts)
        if tts != before:
            changed = True

    if changed:
        agent.tts_config = tts

    # LLM/STT are already standardized in this codebase; no-op for now.
    return changed


def main() -> None:
    session = SessionLocal()
    try:
        agents = session.query(Agent).all()
        logger.info("Loaded %d agents for normalization", len(agents))

        updated = 0
        for agent in agents:
            if _normalize_agent(agent):
                updated += 1

        if updated:
            session.commit()
            logger.info("Normalized %d agents", updated)
        else:
            logger.info("No changes needed; all agents already normalized")
    finally:
        session.close()


if __name__ == "__main__":
    main()