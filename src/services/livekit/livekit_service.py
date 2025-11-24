import logging
import uuid
import asyncio
from typing import Optional, Dict, Any
from livekit import api
from livekit.agents import AgentServer, JobContext, cli
from livekit.agents.voice import AgentSession
from livekit.plugins import silero

from services.agents.voicebot_service import VoicebotService
from services.agents_admin.agent_service import AgentService

logger = logging.getLogger(__name__)

class LiveKitService:
    """
    Service pour gérer les connexions LiveKit et les agents.
    """
    
    def __init__(self, livekit_url: str = "http://localhost:7880", 
                 api_key: str = "devkey", api_secret: str = "secret"):
        self.livekit_url = livekit_url
        self.api_key = api_key
        self.api_secret = api_secret
        self.agent_server = AgentServer()
        self.active_sessions: Dict[str, AgentSession] = {}
        
        # Initialiser les services existants
        self.voicebot_service = VoicebotService()
        self.agent_service = AgentService()
        
        # Enregistrer les handlers d'agents
        self._register_agent_handlers()
    
    def _register_agent_handlers(self):
        """Enregistrer les handlers pour différents types d'agents"""
        
        @self.agent_server.rtc_session()
        async def handle_voicebot_session(ctx: JobContext):
            """Handler pour les sessions voicebot"""
            agent_id = ctx.room.name.split("_")[-1] if "_" in ctx.room.name else "default"
            session_id = str(uuid.uuid4())
            
            logger.info(f"🎯 Starting LiveKit session for agent {agent_id} in room {ctx.room.name}")
            
            try:
                # Récupérer la configuration de l'agent
                agent_config = await self.agent_service.get_agent_config(agent_id)
                if not agent_config:
                    logger.error(f"❌ Agent config not found for {agent_id}")
                    return
                
                # Créer la session LiveKit avec notre agent existant
                session = AgentSession(
                    stt=agent_config.get("stt_provider", "deepgram/nova-2"),
                    llm=agent_config.get("llm_provider", "openai/gpt-4"),
                    tts=agent_config.get("tts_provider", "elevenlabs/rachel"),
                    vad=silero.VAD.load(),
                    allow_interruptions=True
                )
                
                # Stocker la session
                self.active_sessions[session_id] = session
                
                # Démarrer la session avec notre agent
                await session.start(
                    room=ctx.room,
                    agent=self.voicebot_service.create_agent_from_config(agent_config)
                )
                
                logger.info(f"✅ LiveKit session started successfully for agent {agent_id}")
                
            except Exception as e:
                logger.error(f"❌ Failed to start LiveKit session: {e}")
                raise
    
    async def create_room_for_agent(self, agent_id: str) -> Dict[str, Any]:
        """
        Créer une salle LiveKit pour un agent spécifique.
        
        Args:
            agent_id: ID de l'agent à connecter
            
        Returns:
            Dict contenant room_name et token d'accès
        """
        try:
            # Générer un nom de salle unique
            room_name = f"voicebot_{agent_id}_{uuid.uuid4().hex[:8]}"
            
            # Créer la salle via API LiveKit
            room_client = api.RoomServiceClient(self.livekit_url, self.api_key, self.api_secret)
            
            # Créer la salle
            room = await room_client.create_room(
                name=room_name,
                empty_timeout=300,  # 5 minutes
                max_participants=2   # User + Agent
            )
            
            # Générer un token pour le frontend
            token = api.AccessToken(self.api_key, self.api_secret) \
                .with_identity(f"user_{uuid.uuid4().hex[:8]}") \
                .with_name("User") \
                .with_grants(api.VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True
                ))
            
            access_token = token.to_jwt()
            
            logger.info(f"✅ Created LiveKit room {room_name} for agent {agent_id}")
            
            return {
                "room_name": room_name,
                "access_token": access_token,
                "livekit_url": self.livekit_url.replace("http", "ws")
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to create LiveKit room: {e}")
            raise
    
    async def notify_agent_to_join(self, agent_id: str, room_name: str):
        """
        Notifier un agent de rejoindre une salle LiveKit.
        
        Args:
            agent_id: ID de l'agent
            room_name: Nom de la salle à rejoindre
        """
        try:
            # Cette méthode sera appelée par notre endpoint /job
            # Pour l'instant, nous utilisons le système de jobs LiveKit
            # qui se déclenche automatiquement quand un participant rejoint
            
            logger.info(f"📨 Notified agent {agent_id} to join room {room_name}")
            
            # Le handler d'agent sera automatiquement appelé quand l'agent rejoint
            # via le système de jobs LiveKit
            
        except Exception as e:
            logger.error(f"❌ Failed to notify agent: {e}")
            raise
    
    async def cleanup_session(self, session_id: str):
        """Nettoyer une session terminée"""
        if session_id in self.active_sessions:
            session = self.active_sessions.pop(session_id)
            try:
                await session.aclose()
                logger.info(f"🧹 Cleaned up LiveKit session {session_id}")
            except Exception as e:
                logger.error(f"❌ Error cleaning up session {session_id}: {e}")
    
    def run_server(self):
        """Démarrer le serveur d'agents LiveKit"""
        logger.info("🚀 Starting LiveKit Agent Server")
        cli.run_app(self.agent_server)

# Instance globale du service
livekit_service = LiveKitService()