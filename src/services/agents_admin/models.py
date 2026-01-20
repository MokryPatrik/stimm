"""
Pydantic models for agent management API.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator


class ProviderConfig(BaseModel):
    """Configuration for a single provider."""

    provider: str = Field(..., description="Provider name (e.g., 'groq.com', 'async.ai')")
    config: Dict[str, Any] = Field(default_factory=dict, description="Provider-specific configuration")

    @validator("provider")
    def validate_provider(cls, v):
        """Validate provider name."""
        if not v or not v.strip():
            raise ValueError("Provider name cannot be empty")
        return v.strip()


class AgentCreate(BaseModel):
    """Model for creating a new agent."""

    name: str = Field(..., min_length=1, max_length=255, description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")
    system_prompt: Optional[str] = Field(None, description="System prompt for the agent")
    llm_config: ProviderConfig = Field(..., description="LLM provider configuration")
    tts_config: ProviderConfig = Field(..., description="TTS provider configuration")
    stt_config: ProviderConfig = Field(..., description="STT provider configuration")
    is_default: bool = Field(False, description="Whether this agent should be the default")
    rag_config_id: Optional[UUID] = Field(None, description="Optional RAG configuration ID")

    @validator("name")
    def validate_name(cls, v):
        """Validate agent name."""
        if not v or not v.strip():
            raise ValueError("Agent name cannot be empty")
        return v.strip()


class AgentUpdate(BaseModel):
    """Model for updating an existing agent."""

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")
    system_prompt: Optional[str] = Field(None, description="System prompt for the agent")
    llm_config: Optional[ProviderConfig] = Field(None, description="LLM provider configuration")
    tts_config: Optional[ProviderConfig] = Field(None, description="TTS provider configuration")
    stt_config: Optional[ProviderConfig] = Field(None, description="STT provider configuration")
    is_default: Optional[bool] = Field(None, description="Whether this agent should be the default")
    is_active: Optional[bool] = Field(None, description="Whether this agent is active")
    rag_config_id: Optional[UUID] = Field(None, description="Optional RAG configuration ID")


class AgentResponse(BaseModel):
    """Response model for agent data."""

    id: UUID
    user_id: UUID
    name: str
    description: Optional[str]
    system_prompt: Optional[str]
    rag_config_id: Optional[UUID]
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

    class Config:
        from_attributes = True


class AgentListResponse(BaseModel):
    """Response model for listing agents."""

    agents: List[AgentResponse]
    total: int


class AgentConfig(BaseModel):
    """Configuration model for agent runtime usage."""

    llm_provider: str
    tts_provider: str
    stt_provider: str
    system_prompt: Optional[str] = None
    rag_config_id: Optional[UUID] = None
    llm_config: Dict[str, Any]
    tts_config: Dict[str, Any]
    stt_config: Dict[str, Any]

    @classmethod
    def from_agent_response(cls, agent: AgentResponse) -> "AgentConfig":
        """Create AgentConfig from AgentResponse."""
        return cls(
            llm_provider=agent.llm_provider,
            tts_provider=agent.tts_provider,
            stt_provider=agent.stt_provider,
            system_prompt=agent.system_prompt,
            rag_config_id=agent.rag_config_id,
            llm_config=agent.llm_config,
            tts_config=agent.tts_config,
            stt_config=agent.stt_config,
        )


class AgentSessionCreate(BaseModel):
    """Model for creating an agent session."""

    agent_id: UUID
    session_type: str = Field(..., description="Session type: 'stimm', 'chat', 'tts', 'stt'")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")

    @validator("session_type")
    def validate_session_type(cls, v):
        """Validate session type."""
        valid_types = {"stimm", "chat", "tts", "stt"}
        if v not in valid_types:
            raise ValueError(f"Session type must be one of: {', '.join(valid_types)}")
        return v


# ==================== Agent Tools Models ====================


class AgentToolCreate(BaseModel):
    """Model for adding a tool to an agent."""

    tool_slug: str = Field(..., min_length=1, description="Tool slug (e.g., 'product_search')")
    integration_slug: str = Field(..., min_length=1, description="Integration slug (e.g., 'wordpress')")
    integration_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Integration configuration (API keys, URLs, etc.)"
    )

    @validator("tool_slug", "integration_slug")
    def validate_slugs(cls, v):
        """Validate slug format."""
        if not v or not v.strip():
            raise ValueError("Slug cannot be empty")
        return v.strip().lower()


class AgentToolUpdate(BaseModel):
    """Model for updating a tool configuration."""

    integration_slug: Optional[str] = Field(None, description="New integration slug")
    integration_config: Optional[Dict[str, Any]] = Field(None, description="Updated integration configuration")
    is_enabled: Optional[bool] = Field(None, description="Enable or disable the tool")


class AgentToolResponse(BaseModel):
    """Response model for an agent tool."""

    id: UUID
    agent_id: UUID
    tool_slug: str
    integration_slug: str
    integration_config: Dict[str, Any]
    is_enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AgentToolsListResponse(BaseModel):
    """Response model for listing agent tools."""

    tools: List[AgentToolResponse]
    total: int


class ToolFieldDefinition(BaseModel):
    """Definition of a configuration field for a tool integration."""

    name: str
    type: str = Field(..., description="Field type: 'string', 'number', 'boolean', 'select'")
    label: str
    description: Optional[str] = None
    required: bool = True
    default: Optional[Any] = None
    options: Optional[List[str]] = Field(None, description="Options for 'select' type fields")


class IntegrationDefinition(BaseModel):
    """Definition of an integration for a tool."""

    slug: str
    name: str
    description: str
    fields: List[ToolFieldDefinition]


class ToolDefinition(BaseModel):
    """Definition of an available tool."""

    slug: str
    name: str
    description: str
    parameters: Dict[str, Any] = Field(..., description="OpenAI function calling parameters schema")
    integrations: List[IntegrationDefinition]


class AvailableToolsResponse(BaseModel):
    """Response model for listing all available tools and integrations."""

    tools: List[ToolDefinition]
