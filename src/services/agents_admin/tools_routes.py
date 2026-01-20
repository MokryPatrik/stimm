"""
Agent Tools Management API Routes

This module provides FastAPI routes for managing agent tools, including:
- CRUD operations for agent tool configurations
- Listing available tools and integrations
- Tool configuration validation
"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database.session import get_db
from services.tools import get_tool_registry

from .agent_service import AgentService
from .exceptions import AgentNotFoundError, AgentValidationError
from .models import (
    AgentToolCreate,
    AgentToolResponse,
    AgentToolsListResponse,
    AgentToolUpdate,
    AvailableToolsResponse,
    IntegrationDefinition,
    ToolDefinition,
    ToolFieldDefinition,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["agent-tools"])


# ==================== Global Tools Routes ====================


@router.get("/tools/available", response_model=AvailableToolsResponse)
async def get_available_tools():
    """
    Get all available tools with their integrations and configuration fields.
    
    This endpoint returns the catalog of all tools that can be added to agents,
    along with the available integrations for each tool and the configuration
    fields required for each integration.
    """
    try:
        registry = get_tool_registry()
        tools_data = registry.get_available_tools()
        
        tools = []
        for tool_slug, data in tools_data.items():
            integrations = []
            for integration_info in data.get("integrations", []):
                integration_slug = integration_info["value"]
                field_defs_raw = data.get("field_definitions", {}).get(integration_slug, {})
                
                fields = []
                for field_name, field_info in field_defs_raw.items():
                    fields.append(ToolFieldDefinition(
                        name=field_name,
                        type=field_info.get("type", "string"),
                        label=field_info.get("label", field_name),
                        description=field_info.get("description"),
                        required=field_info.get("required", True),
                        default=field_info.get("default"),
                        options=field_info.get("options"),
                    ))
                
                integrations.append(IntegrationDefinition(
                    slug=integration_slug,
                    name=integration_info["label"],
                    description=f"{integration_info['label']} integration for {data['name']}",
                    fields=fields,
                ))
            
            tools.append(ToolDefinition(
                slug=tool_slug,
                name=data["name"],
                description=data["description"],
                parameters=data["parameters"],
                integrations=integrations,
            ))
        
        return AvailableToolsResponse(tools=tools)
    
    except Exception as e:
        logger.error(f"Failed to get available tools: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load available tools"
        )


@router.get(
    "/tools/{tool_slug}/integrations/{integration_slug}/fields",
    response_model=Dict[str, Any]
)
async def get_integration_fields(tool_slug: str, integration_slug: str):
    """
    Get configuration field definitions for a specific tool integration.
    
    This is useful when you need to dynamically render a form for
    configuring a specific integration.
    """
    try:
        registry = get_tool_registry()
        field_definitions = registry.get_field_definitions(tool_slug, integration_slug)
        
        return field_definitions or {}
    
    except Exception as e:
        logger.error(f"Failed to get fields for {tool_slug}.{integration_slug}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get field definitions for {tool_slug}.{integration_slug}"
        )


# ==================== Agent Tools Routes ====================


@router.get("/agents/{agent_id}/tools", response_model=List[AgentToolResponse])
async def get_agent_tools(agent_id: str, db: Session = Depends(get_db)):
    """
    Get all tools configured for an agent.
    
    Returns both enabled and disabled tools.
    """
    agent_service = AgentService(db)
    try:
        tools = agent_service.get_agent_tools(agent_id)
        return [AgentToolResponse(**tool) for tool in tools]
    
    except AgentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID {agent_id} not found"
        )
    except Exception as e:
        logger.error(f"Failed to get tools for agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get agent tools"
        )


@router.post(
    "/agents/{agent_id}/tools",
    response_model=AgentToolResponse,
    status_code=status.HTTP_201_CREATED
)
async def add_agent_tool(
    agent_id: str,
    tool_data: AgentToolCreate,
    db: Session = Depends(get_db)
):
    """
    Add a tool to an agent.
    
    The tool must be one of the available tools (see /tools/available),
    and the integration must be valid for that tool.
    """
    agent_service = AgentService(db)
    try:
        tool = agent_service.add_agent_tool(
            agent_id=agent_id,
            tool_slug=tool_data.tool_slug,
            integration_slug=tool_data.integration_slug,
            integration_config=tool_data.integration_config,
        )
        return AgentToolResponse(**tool)
    
    except AgentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except AgentValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to add tool to agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add tool to agent"
        )


@router.put("/agents/{agent_id}/tools/{tool_slug}", response_model=AgentToolResponse)
async def update_agent_tool(
    agent_id: str,
    tool_slug: str,
    tool_data: AgentToolUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a tool configuration for an agent.
    
    Can update the integration, configuration, or enabled status.
    Configuration updates are merged with existing config.
    """
    agent_service = AgentService(db)
    try:
        tool = agent_service.update_agent_tool(
            agent_id=agent_id,
            tool_slug=tool_slug,
            integration_slug=tool_data.integration_slug,
            integration_config=tool_data.integration_config,
            is_enabled=tool_data.is_enabled,
        )
        return AgentToolResponse(**tool)
    
    except AgentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except AgentValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update tool {tool_slug} for agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update agent tool"
        )


@router.delete(
    "/agents/{agent_id}/tools/{tool_slug}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def remove_agent_tool(
    agent_id: str,
    tool_slug: str,
    db: Session = Depends(get_db)
):
    """
    Remove a tool from an agent.
    
    This permanently deletes the tool configuration for this agent.
    """
    agent_service = AgentService(db)
    try:
        agent_service.remove_agent_tool(agent_id=agent_id, tool_slug=tool_slug)
    
    except AgentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to remove tool {tool_slug} from agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove tool from agent"
        )


@router.put(
    "/agents/{agent_id}/tools/{tool_slug}/enable",
    response_model=AgentToolResponse
)
async def enable_agent_tool(
    agent_id: str,
    tool_slug: str,
    db: Session = Depends(get_db)
):
    """Enable a tool for an agent."""
    agent_service = AgentService(db)
    try:
        tool = agent_service.update_agent_tool(
            agent_id=agent_id,
            tool_slug=tool_slug,
            is_enabled=True,
        )
        return AgentToolResponse(**tool)
    
    except AgentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to enable tool {tool_slug} for agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enable tool"
        )


@router.put(
    "/agents/{agent_id}/tools/{tool_slug}/disable",
    response_model=AgentToolResponse
)
async def disable_agent_tool(
    agent_id: str,
    tool_slug: str,
    db: Session = Depends(get_db)
):
    """Disable a tool for an agent without removing it."""
    agent_service = AgentService(db)
    try:
        tool = agent_service.update_agent_tool(
            agent_id=agent_id,
            tool_slug=tool_slug,
            is_enabled=False,
        )
        return AgentToolResponse(**tool)
    
    except AgentNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to disable tool {tool_slug} for agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable tool"
        )
