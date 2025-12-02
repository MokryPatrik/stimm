"""
RAG Configuration Management API Routes

This module provides FastAPI routes for managing RAG configurations, including:
- CRUD operations for RAG configs
- Default RAG config management
- Provider configuration management
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .rag_config_service import RagConfigService
from .config_models import (
    RagConfigCreate,
    RagConfigUpdate,
    RagConfigResponse,
    RagConfigListResponse,
    ProviderConfig,
)
from services.agents_admin.exceptions import (
    AgentNotFoundError,
    AgentAlreadyExistsError,
    AgentValidationError,
)
from database.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag-configs", tags=["rag-configs"])


@router.get("/", response_model=List[RagConfigResponse])
async def list_rag_configs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all RAG configurations with pagination"""
    rag_config_service = RagConfigService(db)
    configs_result = rag_config_service.list_rag_configs(skip=skip, limit=limit)
    return configs_result.configs


@router.get("/{rag_config_id}", response_model=RagConfigResponse)
async def get_rag_config(
    rag_config_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific RAG configuration by ID"""
    rag_config_service = RagConfigService(db)
    try:
        rag_config = rag_config_service.get_rag_config(rag_config_id)
        return rag_config
    except AgentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RAG configuration with ID {rag_config_id} not found"
        )


@router.post("/", response_model=RagConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_rag_config(
    rag_config_data: RagConfigCreate,
    db: Session = Depends(get_db)
):
    """Create a new RAG configuration"""
    rag_config_service = RagConfigService(db)
    try:
        rag_config = rag_config_service.create_rag_config(rag_config_data)
        return rag_config
    except AgentValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "errors": [str(e)]}
        )
    except AgentAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": str(e), "errors": [str(e)]}
        )
    except Exception as e:
        logger.error(f"Failed to create RAG configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to create RAG configuration", "errors": [str(e)]}
        )


@router.put("/{rag_config_id}", response_model=RagConfigResponse)
async def update_rag_config(
    rag_config_id: str,
    rag_config_data: RagConfigUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing RAG configuration"""
    rag_config_service = RagConfigService(db)
    try:
        rag_config = rag_config_service.update_rag_config(rag_config_id, rag_config_data)
        return rag_config
    except AgentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RAG configuration with ID {rag_config_id} not found"
        )
    except AgentValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except AgentAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update RAG configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update RAG configuration"
        )


@router.delete("/{rag_config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rag_config(
    rag_config_id: str,
    db: Session = Depends(get_db)
):
    """Delete a RAG configuration"""
    rag_config_service = RagConfigService(db)
    try:
        rag_config_service.delete_rag_config(rag_config_id)
    except AgentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RAG configuration with ID {rag_config_id} not found"
        )
    except AgentValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to delete RAG configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete RAG configuration"
        )


@router.get("/default/current", response_model=RagConfigResponse)
async def get_default_rag_config(
    db: Session = Depends(get_db)
):
    """Get the current default RAG configuration"""
    rag_config_service = RagConfigService(db)
    try:
        rag_config = rag_config_service.get_default_rag_config()
        return rag_config
    except AgentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No default RAG configuration found"
        )


@router.put("/{rag_config_id}/set-default", response_model=RagConfigResponse)
async def set_default_rag_config(
    rag_config_id: str,
    db: Session = Depends(get_db)
):
    """Set a RAG configuration as the default"""
    rag_config_service = RagConfigService(db)
    try:
        rag_config = rag_config_service.set_default_rag_config(rag_config_id)
        return rag_config
    except AgentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RAG configuration with ID {rag_config_id} not found"
        )
    except Exception as e:
        logger.error(f"Failed to set default RAG configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set default RAG configuration"
        )


@router.get("/providers/available", response_model=Dict[str, Any])
async def get_available_rag_providers():
    """Get available RAG providers with their expected properties"""
    try:
        from services.agents_admin.provider_registry import get_provider_registry

        registry = get_provider_registry()
        providers_data = registry.get_available_providers()

        # Extract only RAG providers
        rag_providers = providers_data.get("rag", {})
        return rag_providers
    except Exception as e:
        logger.error(f"Failed to load available RAG providers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load available RAG providers"
        )


@router.get("/providers/{provider_name}/fields", response_model=Dict[str, Any])
async def get_rag_provider_fields(provider_name: str):
    """Get field definitions for a specific RAG provider"""
    try:
        from services.agents_admin.provider_registry import get_provider_registry

        registry = get_provider_registry()
        field_definitions = registry.get_provider_field_definitions("rag", provider_name)

        # Return empty dict if provider has no configurable fields
        return field_definitions or {}
    except Exception as e:
        logger.error(f"Failed to get provider fields for rag.{provider_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get field definitions for provider rag.{provider_name}"
        )