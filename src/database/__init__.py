"""
Database package for voicebot application.
"""
from .session import get_db, get_engine
from .models import Base, User, Agent, AgentSession

# For backward compatibility, provide engine as a property
engine = get_engine()

__all__ = [
    "get_db",
    "engine",
    "Base",
    "User",
    "Agent",
    "AgentSession"
]