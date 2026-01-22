"""
Product RAG Sync Service - Orchestrates product sync and RAG indexing.

This is the main entry point for product synchronization. It coordinates:
1. Fetching products from e-commerce platforms (WooCommerce, Shopify, etc.)
2. Storing them in the local products table (via ProductSyncService)
3. Embedding changed products into RAG (via ProductRagManager)

The two-stage architecture enables:
- Incremental updates (only changed products are re-embedded)
- Resumable syncs (products are persisted before embedding)
- Better visibility into sync state
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy.orm import Session

from database import Agent, AgentTool, RagConfig
from database.session import SessionLocal

logger = logging.getLogger(__name__)


class ProductRagSyncService:
    """
    Service for orchestrating product sync and RAG indexing.
    
    This service coordinates:
    1. ProductSyncService - fetches products and stores in DB
    2. ProductRagManager - embeds changed products into Qdrant
    """

    def __init__(self, db_session: Session = None):
        self.db_session = db_session
        self._running_syncs: Dict[str, bool] = {}

    def _get_session(self) -> Session:
        """Get database session."""
        if self.db_session:
            return self.db_session
        return SessionLocal()

    def _get_sync_key(self, agent_id: UUID, tool_slug: str) -> str:
        """Generate a unique key for tracking sync status."""
        return f"{agent_id}:{tool_slug}"

    def is_sync_running(self, agent_id: UUID, tool_slug: str) -> bool:
        """Check if a sync is currently running for this agent/tool."""
        key = self._get_sync_key(agent_id, tool_slug)
        return self._running_syncs.get(key, False)

    async def sync_products_for_agent(
        self,
        agent_id: UUID,
        tool_slug: str = "product_stock",
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Full sync: fetch products from source, store in DB, and index to RAG.
        
        Args:
            agent_id: Agent ID
            tool_slug: Tool slug (default: product_stock)
            force: Force sync even if recently synced
            
        Returns:
            Sync result with status and statistics
        """
        from services.tools import get_tool_registry
        from services.tools.product_sync_service import get_product_sync_service
        from services.tools.product_rag_manager import get_product_rag_manager
        
        sync_key = self._get_sync_key(agent_id, tool_slug)
        if self._running_syncs.get(sync_key, False):
            logger.info(f"Sync already running for {sync_key}, skipping")
            return {
                "success": True,
                "skipped": True,
                "message": "Sync already in progress for this agent/tool",
            }
        
        self._running_syncs[sync_key] = True
        session = self._get_session()
        
        try:
            # Get agent tool configuration
            agent_tool = session.query(AgentTool).filter(
                and_(
                    AgentTool.agent_id == agent_id,
                    AgentTool.tool_slug == tool_slug,
                    AgentTool.is_enabled == True,
                )
            ).first()
            
            if not agent_tool:
                return {
                    "success": False,
                    "error": f"Tool {tool_slug} not found or not enabled for agent",
                }
            
            config = agent_tool.integration_config or {}
            
            # Check if RAG sync is enabled
            if not config.get("use_as_rag", False):
                return {
                    "success": False,
                    "error": "RAG sync not enabled for this tool",
                }
            
            # Check sync interval (skip if recently synced, unless forced)
            last_sync = config.get("last_sync_at")
            sync_interval = config.get("sync_interval_hours", 24)
            
            if last_sync and not force:
                last_sync_time = datetime.fromisoformat(last_sync)
                next_sync_time = last_sync_time + timedelta(hours=sync_interval)
                if datetime.utcnow() < next_sync_time:
                    return {
                        "success": True,
                        "skipped": True,
                        "message": f"Sync not due yet. Next sync at {next_sync_time.isoformat()}",
                        "last_sync": last_sync,
                    }
            
            # Get agent's RAG config
            agent = session.query(Agent).filter(Agent.id == agent_id).first()
            if not agent or not agent.rag_config_id:
                return {
                    "success": False,
                    "error": "Agent has no RAG configuration. Please assign a RAG config first.",
                }
            
            rag_config = session.query(RagConfig).filter(RagConfig.id == agent.rag_config_id).first()
            if not rag_config:
                return {
                    "success": False,
                    "error": "RAG configuration not found",
                }
            
            # Get integration class
            registry = get_tool_registry()
            integration_class = registry.get_integration_class(
                agent_tool.tool_slug,
                agent_tool.integration_slug,
            )
            
            if not integration_class:
                return {
                    "success": False,
                    "error": f"Integration {agent_tool.integration_slug} not found",
                }
            
            # Create integration instance
            integration = integration_class(agent_tool.integration_config)
            
            try:
                # Stage 1: Fetch products from source
                # Use last_sync_at for incremental sync (only fetch modified products)
                modified_after = None
                if last_sync and not force:
                    modified_after = last_sync
                    logger.info(f"Incremental sync: fetching products modified after {modified_after}")
                else:
                    logger.info("Full sync: fetching all products")
                
                if not hasattr(integration, "fetch_all_products"):
                    return {
                        "success": False,
                        "error": f"Integration {agent_tool.integration_slug} doesn't support bulk fetch",
                    }
                
                products = await integration.fetch_all_products(modified_after=modified_after)
                logger.info(f"Fetched {len(products)} products from source")
                
                if not products:
                    return {
                        "success": True,
                        "products_fetched": 0,
                        "message": "No products found in source",
                    }
                
                # Stage 2: Sync to local database
                logger.info("Syncing products to local database...")
                product_sync_service = get_product_sync_service()
                db_result = await product_sync_service.sync_products_to_db(
                    agent_tool=agent_tool,
                    products=products,
                )
                
                if not db_result.get("success"):
                    return {
                        "success": False,
                        "error": f"Failed to sync products to database: {db_result.get('error')}",
                    }
                
                logger.info(
                    f"Database sync complete: {db_result.get('new')} new, "
                    f"{db_result.get('updated')} updated, {db_result.get('deleted')} deleted"
                )
                
                # Stage 3: Index changed products to RAG
                logger.info("Indexing products to RAG...")
                rag_manager = get_product_rag_manager()
                rag_result = await rag_manager.index_pending_products(
                    agent_id=agent_id,
                    tool_slug=tool_slug,
                )
                
                if not rag_result.get("success"):
                    return {
                        "success": False,
                        "error": f"Failed to index products to RAG: {rag_result.get('error')}",
                        "db_sync": db_result,
                    }
                
                logger.info(f"RAG indexing complete: {rag_result.get('indexed')} products indexed")
                
                # Stage 4: Clean up deleted products from RAG
                if db_result.get("deleted", 0) > 0:
                    logger.info("Cleaning up deleted products from RAG...")
                    await rag_manager.remove_deleted_products(
                        agent_id=agent_id,
                        tool_slug=tool_slug,
                    )
                
                # Update last sync timestamp
                config["last_sync_at"] = datetime.utcnow().isoformat()
                config["last_sync_count"] = len(products)
                agent_tool.integration_config = config
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(agent_tool, "integration_config")
                session.commit()
                
                return {
                    "success": True,
                    "products_fetched": len(products),
                    "db_sync": {
                        "new": db_result.get("new", 0),
                        "updated": db_result.get("updated", 0),
                        "unchanged": db_result.get("unchanged", 0),
                        "deleted": db_result.get("deleted", 0),
                    },
                    "rag_indexed": rag_result.get("indexed", 0),
                }
                
            finally:
                await integration.close()
            
        except Exception as e:
            logger.error(f"Error syncing products for agent {agent_id}: {e}")
            return {
                "success": False,
                "error": str(e),
            }
        finally:
            self._running_syncs[sync_key] = False
            if self.db_session is None:
                session.close()

    async def index_only(
        self,
        agent_id: UUID,
        tool_slug: str = "product_stock",
    ) -> Dict[str, Any]:
        """
        Only index pending products to RAG (no fetch from source).
        
        Useful when products were synced but RAG indexing failed or was interrupted.
        
        Args:
            agent_id: Agent ID
            tool_slug: Tool slug
            
        Returns:
            Indexing result
        """
        from services.tools.product_rag_manager import get_product_rag_manager
        
        rag_manager = get_product_rag_manager()
        return await rag_manager.index_pending_products(
            agent_id=agent_id,
            tool_slug=tool_slug,
        )

    async def sync_all_agents(self) -> Dict[str, Any]:
        """
        Sync products for all agents that have RAG sync enabled.
        
        Returns:
            Summary of sync results for all agents
        """
        session = self._get_session()
        
        try:
            # Find all agent tools with use_as_rag enabled
            # Check both product_stock (new) and product_search (legacy)
            agent_tools = session.query(AgentTool).filter(
                and_(
                    AgentTool.tool_slug.in_(["product_stock", "product_search"]),
                    AgentTool.is_enabled == True,
                    AgentTool.integration_config["use_as_rag"].astext == "true",
                )
            ).all()
            
            logger.info(f"Found {len(agent_tools)} agents with RAG sync enabled")
            
            results = {}
            for tool in agent_tools:
                agent_id = str(tool.agent_id)
                logger.info(f"Syncing products for agent {agent_id}...")
                
                result = await self.sync_products_for_agent(
                    agent_id=tool.agent_id,
                    tool_slug=tool.tool_slug,
                    force=False,
                )
                
                results[agent_id] = result
            
            return {
                "success": True,
                "agents_processed": len(agent_tools),
                "results": results,
            }
            
        except Exception as e:
            logger.error(f"Error in sync_all_agents: {e}")
            return {
                "success": False,
                "error": str(e),
            }
        finally:
            if self.db_session is None:
                session.close()

    def get_sync_status(
        self,
        agent_id: UUID,
        tool_slug: str = "product_stock",
    ) -> Dict[str, Any]:
        """
        Get detailed sync status for an agent/tool.
        
        Returns:
            Sync status including DB stats, RAG stats, and last sync info
        """
        from services.tools.product_rag_manager import get_product_rag_manager
        
        session = self._get_session()
        
        try:
            agent_tool = session.query(AgentTool).filter(
                and_(
                    AgentTool.agent_id == agent_id,
                    AgentTool.tool_slug == tool_slug,
                )
            ).first()
            
            if not agent_tool:
                return {"error": "Agent tool not found"}
            
            config = agent_tool.integration_config or {}
            
            # Get RAG stats
            rag_manager = get_product_rag_manager()
            rag_stats = rag_manager.get_index_stats(agent_id, tool_slug)
            
            return {
                "agent_id": str(agent_id),
                "tool_slug": tool_slug,
                "rag_sync_enabled": config.get("use_as_rag", False),
                "last_sync_at": config.get("last_sync_at"),
                "last_sync_count": config.get("last_sync_count", 0),
                "sync_interval_hours": config.get("sync_interval_hours", 24),
                "is_syncing": self.is_sync_running(agent_id, tool_slug),
                **rag_stats,
            }
            
        finally:
            if self.db_session is None:
                session.close()


# Global service instance
_product_rag_sync_service: Optional[ProductRagSyncService] = None


def get_product_rag_sync_service() -> ProductRagSyncService:
    """Get the global product RAG sync service instance."""
    global _product_rag_sync_service
    if _product_rag_sync_service is None:
        _product_rag_sync_service = ProductRagSyncService()
    return _product_rag_sync_service
