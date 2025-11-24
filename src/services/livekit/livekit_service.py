import logging
import uuid
from typing import Dict, Any
import livekit

from services.agents.voicebot_service import get_voicebot_service
from services.agents_admin.agent_service import AgentService

logger = logging.getLogger(__name__)

class LiveKitService:
    """
    Service pour gérer les connexions LiveKit et générer des tokens d'accès.
    """
    
    def __init__(self, livekit_url: str = "http://localhost:7880",
                 api_key: str = "devkey", api_secret: str = "secret"):
        self.livekit_url = livekit_url
        self.api_key = api_key
        self.api_secret = api_secret
        
        # Initialiser les services existants
        self.voicebot_service = get_voicebot_service()
        self.agent_service = AgentService()
    
    async def create_room_for_agent(self, agent_id: str) -> Dict[str, Any]:
        """
        Générer un token d'accès pour une salle LiveKit.
        
        Args:
            agent_id: ID de l'agent à connecter
            
        Returns:
            Dict contenant room_name et token d'accès
        """
        try:
            # Générer un nom de salle unique
            room_name = f"voicebot_{agent_id}_{uuid.uuid4().hex[:8]}"
            
            # Générer un token d'accès pour le frontend
            token = livekit.AccessToken(self.api_key, self.api_secret) \
                .with_identity(f"user_{uuid.uuid4().hex[:8]}") \
                .with_name("User") \
                .with_grants(livekit.VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True
                ))
            
            access_token = token.to_jwt()
            
            logger.info(f"✅ Generated LiveKit token for room {room_name} for agent {agent_id}")
            
            return {
                "room_name": room_name,
                "access_token": access_token,
                "livekit_url": self.livekit_url.replace("http", "ws")
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to generate LiveKit token: {e}")
            raise
    
    async def notify_agent_to_join(self, agent_id: str, room_name: str):
        """
        Notifier un agent de rejoindre une salle LiveKit.
        
        Args:
            agent_id: ID de l'agent
            room_name: Nom de la salle à rejoindre
        """
        try:
            # Ici, nous notifierons notre agent existant de rejoindre la salle
            # via notre propre système de jobs
            logger.info(f"📨 Notified agent {agent_id} to join room {room_name}")
            
            # TODO: Implémenter la logique pour notifier notre agent
            # via notre système de jobs existant
            
        except Exception as e:
            logger.error(f"❌ Failed to notify agent: {e}")
            raise

# Instance globale du service
livekit_service = LiveKitService()