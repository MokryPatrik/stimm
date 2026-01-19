import logging
from typing import Any, Dict, Optional

from services.agents.stimm_service import StimmService
from services.livekit.agent_bridge import create_agent_bridge
from services.rag.chatbot_service import chatbot_service
from services.stt.stt import STTService
from services.tts.tts import TTSService
from services.vad.silero_service import SileroVADService

logger = logging.getLogger(__name__)

# Default greeting for SIP calls
DEFAULT_SIP_GREETING = "Dobrý deň, som váš virtuálny asistent. Ako vám môžem pomôcť?"


async def create_agent_session(
    agent_id: str, 
    room_name: str, 
    token: str, 
    livekit_url: str,
    greeting: Optional[str] = None,
    is_sip_call: bool = False
) -> Dict[str, Any]:
    """
    Creates and initializes a complete Agent Session (Services + Bridge).

    Args:
        agent_id: The agent ID
        room_name: LiveKit room name
        token: LiveKit access token
        livekit_url: LiveKit server URL
        greeting: Optional greeting message to speak on connect
        is_sip_call: Whether this is a SIP phone call (auto-detects from room name if not specified)

    Returns a dictionary containing:
    - stimm_service: The orchestrated service
    - agent_bridge: The connection to LiveKit
    - session_id: Unique session ID
    """
    logger.info(f"🏗️ Creating Agent Session for {agent_id} in {room_name}")

    # Auto-detect SIP call from room name
    if not is_sip_call and room_name.startswith("sip-inbound"):
        is_sip_call = True
        logger.info("📞 Detected SIP inbound call from room name")

    # 1. Initialize Services
    stt = STTService(agent_id=agent_id)
    tts = TTSService(agent_id=agent_id)
    vad = SileroVADService()

    # 2. Initialize Stimm Orchestrator
    stimm = StimmService(stt_service=stt, chatbot_service=chatbot_service, tts_service=tts, vad_service=vad, agent_id=agent_id)

    # 3. Determine Sample Rate
    sample_rate = 24000
    if hasattr(tts, "provider") and hasattr(tts.provider, "sample_rate"):
        sample_rate = tts.provider.sample_rate
        logger.info(f"🎤 Using sample rate {sample_rate}Hz from TTS provider")

    # 4. Create Agent Bridge
    agent_bridge = await create_agent_bridge(agent_id=agent_id, room_name=room_name, token=token, livekit_url=livekit_url, sample_rate=sample_rate)

    agent_bridge.set_stimm_service(stimm)
    
    # 5. For SIP calls, schedule greeting after bridge is connected
    if is_sip_call:
        greeting_text = greeting or DEFAULT_SIP_GREETING
        logger.info(f"📞 SIP call detected - will speak greeting: '{greeting_text}'")
        # Store greeting to be spoken after session starts
        agent_bridge._pending_greeting = greeting_text

    return {"stimm_service": stimm, "agent_bridge": agent_bridge, "session_id": f"{agent_id}_{room_name}"}
