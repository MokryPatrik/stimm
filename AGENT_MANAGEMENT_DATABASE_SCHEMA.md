# Agent Management Database Schema

## Database Design

### PostgreSQL Tables

#### Users Table (Future IAM Support)
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- System user for default/dev agents
INSERT INTO users (id, username, email) VALUES 
('00000000-0000-0000-0000-000000000000', 'system', 'system@voicebot.local');
```

#### Agents Table
```sql
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Provider selections
    llm_provider VARCHAR(50) NOT NULL,
    tts_provider VARCHAR(50) NOT NULL, 
    stt_provider VARCHAR(50) NOT NULL,
    
    -- Provider configurations (JSONB for flexibility)
    llm_config JSONB NOT NULL DEFAULT '{}',
    tts_config JSONB NOT NULL DEFAULT '{}',
    stt_config JSONB NOT NULL DEFAULT '{}',
    
    -- Agent settings
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    is_system_agent BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_agents_user_id ON agents(user_id);
CREATE INDEX idx_agents_is_default ON agents(is_default) WHERE is_default = TRUE;
CREATE INDEX idx_agents_is_active ON agents(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_agents_is_system ON agents(is_system_agent) WHERE is_system_agent = TRUE;

-- Constraint: Only one default agent per user
CREATE UNIQUE INDEX idx_agents_user_default ON agents(user_id) WHERE is_default = TRUE;
```

#### Agent Sessions Table (For runtime agent switching)
```sql
CREATE TABLE agent_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    session_type VARCHAR(50) NOT NULL, -- 'voicebot', 'chat', 'tts', 'stt'
    ip_address INET,
    user_agent TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_agent_sessions_user_agent ON agent_sessions(user_id, agent_id);
CREATE INDEX idx_agent_sessions_expires ON agent_sessions(expires_at);
```

## Configuration Schema Examples

### LLM Provider Configuration
```json
{
  "llm_provider": "groq.com",
  "llm_config": {
    "api_key": "sk_...",
    "model": "llama-3.1-8b-instant",
    "api_url": "https://api.groq.com",
    "completions_path": "/openai/v1/chat/completions",
    "temperature": 0.7,
    "max_tokens": 1000
  }
}
```

### TTS Provider Configuration  
```json
{
  "tts_provider": "async.ai",
  "tts_config": {
    "api_key": "sk_...",
    "voice_id": "e7b694f8-d277-47ff-82bf-cb48e7662647",
    "model_id": "asyncflow_v2.0",
    "sample_rate": 44100,
    "encoding": "pcm_s16le",
    "container": "raw"
  }
}
```

### STT Provider Configuration
```json
{
  "stt_provider": "whisper.local", 
  "stt_config": {
    "url": "ws://whisper-stt:8003",
    "path": "/api/stt/stream",
    "language": "fr"
  }
}
```

## Python Models

### SQLAlchemy Models

**File: [`src/voicebot_app/database/models.py`](src/voicebot_app/database/models.py)**

```python
from sqlalchemy import Column, String, Boolean, DateTime, Text, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Provider selections
    llm_provider = Column(String(50), nullable=False)
    tts_provider = Column(String(50), nullable=False)
    stt_provider = Column(String(50), nullable=False)
    
    # Provider configurations
    llm_config = Column(JSONB, nullable=False, default=dict)
    tts_config = Column(JSONB, nullable=False, default=dict) 
    stt_config = Column(JSONB, nullable=False, default=dict)
    
    # Agent settings
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_system_agent = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_agents_user_id', 'user_id'),
        Index('idx_agents_is_default', 'is_default', postgresql_where=is_default.is_(True)),
        Index('idx_agents_is_active', 'is_active', postgresql_where=is_active.is_(True)),
        Index('idx_agents_user_default', 'user_id', unique=True, 
              postgresql_where=is_default.is_(True)),
    )

class AgentSession(Base):
    __tablename__ = "agent_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    session_type = Column(String(50), nullable=False)
    ip_address = Column(String(45))  # IPv6 support
    user_agent = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    
    __table_args__ = (
        Index('idx_agent_sessions_user_agent', 'user_id', 'agent_id'),
        Index('idx_agent_sessions_expires', 'expires_at'),
    )
```

### Pydantic Models for API

**File: [`src/voicebot_app/services/agent/models.py`](src/voicebot_app/services/agent/models.py)**

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

class ProviderConfig(BaseModel):
    provider: str
    config: Dict[str, Any] = Field(default_factory=dict)

class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    llm_config: ProviderConfig
    tts_config: ProviderConfig  
    stt_config: ProviderConfig
    is_default: bool = False

class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    llm_config: Optional[ProviderConfig] = None
    tts_config: Optional[ProviderConfig] = None
    stt_config: Optional[ProviderConfig] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None

class AgentResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    llm_provider: str
    tts_provider: str
    stt_provider: str
    llm_config: Dict[str, Any]
    tts_config: Dict[str, Any]
    stt_config: Dict[str, Any]
    is_default: bool
    is_active: bool
    is_system_agent: bool
    created_at: datetime
    updated_at: datetime

class AgentListResponse(BaseModel):
    agents: list[AgentResponse]
    total: int
```

## Initial Migration

**File: [`alembic/versions/001_initial_agent_schema.py`](alembic/versions/001_initial_agent_schema.py)**

```python
"""Initial agent management schema

Revision ID: 001
Revises: 
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )
    
    # Create agents table
    op.create_table('agents',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('llm_provider', sa.String(length=50), nullable=False),
        sa.Column('tts_provider', sa.String(length=50), nullable=False),
        sa.Column('stt_provider', sa.String(length=50), nullable=False),
        sa.Column('llm_config', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('tts_config', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('stt_config', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('is_default', sa.Boolean(), server_default=sa.text('false'), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=True),
        sa.Column('is_system_agent', sa.Boolean(), server_default=sa.text('false'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_agents_user_id', 'agents', ['user_id'])
    op.create_index('idx_agents_is_default', 'agents', ['is_default'], postgresql_where=sa.text('is_default = true'))
    op.create_index('idx_agents_is_active', 'agents', ['is_active'], postgresql_where=sa.text('is_active = true'))
    op.create_index('idx_agents_user_default', 'agents', ['user_id'], unique=True, postgresql_where=sa.text('is_default = true'))
    
    # Create agent_sessions table
    op.create_table('agent_sessions',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(), nullable=False),
        sa.Column('agent_id', postgresql.UUID(), nullable=False),
        sa.Column('session_type', sa.String(length=50), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index('idx_agent_sessions_user_agent', 'agent_sessions', ['user_id', 'agent_id'])
    op.create_index('idx_agent_sessions_expires', 'agent_sessions', ['expires_at'])
    
    # Insert system user
    op.execute("""
        INSERT INTO users (id, username, email) 
        VALUES ('00000000-0000-0000-0000-000000000000', 'system', 'system@voicebot.local')
    """)

def downgrade():
    op.drop_index('idx_agent_sessions_expires', table_name='agent_sessions')
    op.drop_index('idx_agent_sessions_user_agent', table_name='agent_sessions')
    op.drop_table('agent_sessions')
    
    op.drop_index('idx_agents_user_default', table_name='agents')
    op.drop_index('idx_agents_is_active', table_name='agents')
    op.drop_index('idx_agents_is_default', table_name='agents')
    op.drop_index('idx_agents_user_id', table_name='agents')
    op.drop_table('agents')
    
    op.drop_table('users')
```

## Docker Compose Updates

**File: [`docker-compose.yml`](docker-compose.yml) - Add PostgreSQL service**

```yaml
services:
  postgres:
    image: postgres:15
    container_name: voicebot-postgres
    environment:
      POSTGRES_DB: voicebot
      POSTGRES_USER: voicebot_user
      POSTGRES_PASSWORD: voicebot_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U voicebot_user -d voicebot"]
      interval: 10s
      timeout: 5s
      retries: 5

  voicebot-app:
    # ... existing config
    environment:
      - DATABASE_URL=postgresql://voicebot_user:voicebot_password@postgres:5432/voicebot
    depends_on:
      postgres:
        condition: service_healthy

volumes:
  postgres_data:
```

This database schema provides a solid foundation for the agent management system with proper indexing, constraints, and future IAM support.