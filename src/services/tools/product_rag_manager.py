"""
Product RAG Manager - Handles embedding products into the vector database.

This service handles the second stage of the sync pipeline:
1. Query products table for items needing indexing (rag_indexed=False)
2. Embed them in batches using the configured embedding model
3. Upsert to Qdrant
4. Mark products as indexed

This enables incremental updates - only changed products are re-embedded.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid5, NAMESPACE_URL

from sqlalchemy import and_
from sqlalchemy.orm import Session

from database import Agent, AgentTool, Product, RagConfig
from database.session import SessionLocal

logger = logging.getLogger(__name__)


class ProductRagManager:
    """
    Manager for embedding products into RAG vector database.
    
    This handles incremental indexing - only products with rag_indexed=False
    are processed, making subsequent syncs much faster.
    """

    def __init__(self, db_session: Session = None):
        self.db_session = db_session

    def _get_session(self) -> Session:
        """Get database session."""
        if self.db_session:
            return self.db_session
        return SessionLocal()

    async def index_pending_products(
        self,
        agent_id: UUID,
        tool_slug: str = "product_stock",
        batch_size: int = 500,
    ) -> Dict[str, Any]:
        """
        Index all pending products for an agent.
        
        Args:
            agent_id: Agent ID
            tool_slug: Tool slug (default: product_stock)
            batch_size: Number of products to process per batch
            
        Returns:
            Indexing statistics
        """
        from services.rag.retrieval_engine import RetrievalEngine
        from services.embeddings import is_openai_model
        from qdrant_client.http import models as qmodels
        
        session = self._get_session()
        
        try:
            # Get agent and RAG config
            agent = session.query(Agent).filter(Agent.id == agent_id).first()
            if not agent or not agent.rag_config_id:
                return {
                    "success": False,
                    "error": "Agent has no RAG configuration",
                }
            
            rag_config = session.query(RagConfig).filter(RagConfig.id == agent.rag_config_id).first()
            if not rag_config:
                return {
                    "success": False,
                    "error": "RAG configuration not found",
                }
            
            # Get agent tool
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
                    "error": f"Tool {tool_slug} not found or not enabled",
                }
            
            # Initialize retrieval engine
            provider_config = rag_config.provider_config or {}
            collection_name = provider_config.get("collection_name", "stimm_knowledge")
            embed_model = provider_config.get("embedding_model", "")
            
            engine = RetrievalEngine(
                collection_name=collection_name,
                embed_model_name=embed_model,
                openai_api_key=provider_config.get("openai_api_key"),
            )
            
            # Ensure collection exists
            await engine.ensure_collection(recreate_on_dimension_mismatch=True)
            
            # Embedding batch size (smaller than processing batch)
            embed_batch_size = 100 if is_openai_model(embed_model) else 32
            
            # Track statistics
            stats = {
                "indexed": 0,
                "failed": 0,
                "batches_processed": 0,
            }
            
            source = f"product_sync_{agent_id}"
            
            # Process in batches until no more pending products
            while True:
                # Get pending products
                pending_products = session.query(Product).filter(
                    and_(
                        Product.agent_tool_id == agent_tool.id,
                        Product.rag_indexed == False,
                    )
                ).limit(batch_size).all()
                
                if not pending_products:
                    break
                
                logger.info(f"Processing batch of {len(pending_products)} products for RAG indexing")
                
                try:
                    # Generate embeddings
                    texts = [p.to_rag_text() for p in pending_products]
                    embeddings = engine.embedder.encode(
                        texts,
                        batch_size=embed_batch_size,
                        show_progress_bar=False,
                        normalize_embeddings=True,
                    )
                    
                    # Create Qdrant points
                    points = []
                    product_point_ids = {}
                    
                    for product, embedding in zip(pending_products, embeddings):
                        # Generate deterministic point ID
                        point_id = str(uuid5(NAMESPACE_URL, f"product:{agent_id}:{product.external_id}"))
                        product_point_ids[product.id] = point_id
                        
                        payload = {
                            "text": product.to_rag_text(),
                            "namespace": "products",
                            "source": source,
                            "product_id": product.external_id,
                            "product_name": product.name,
                            "product_db_id": str(product.id),
                        }
                        
                        points.append(
                            qmodels.PointStruct(
                                id=point_id,
                                vector=embedding.tolist(),
                                payload=payload,
                            )
                        )
                    
                    # Upsert to Qdrant
                    engine.client.upsert(collection_name=collection_name, points=points)
                    
                    # Mark products as indexed
                    now = datetime.utcnow()
                    for product in pending_products:
                        product.rag_indexed = True
                        product.rag_indexed_at = now
                        product.qdrant_point_id = product_point_ids.get(product.id)
                    
                    session.commit()
                    
                    stats["indexed"] += len(pending_products)
                    stats["batches_processed"] += 1
                    
                    logger.info(f"Indexed {stats['indexed']} products so far")
                    
                except Exception as e:
                    logger.error(f"Error indexing batch: {e}")
                    stats["failed"] += len(pending_products)
                    session.rollback()
                    # Continue with next batch
                    continue
            
            return {
                "success": True,
                "indexed": stats["indexed"],
                "failed": stats["failed"],
                "batches_processed": stats["batches_processed"],
                "collection": collection_name,
            }
            
        except Exception as e:
            logger.error(f"Error in index_pending_products: {e}")
            return {
                "success": False,
                "error": str(e),
            }
        finally:
            if self.db_session is None:
                session.close()

    async def remove_deleted_products(
        self,
        agent_id: UUID,
        tool_slug: str = "product_stock",
    ) -> Dict[str, Any]:
        """
        Remove products from Qdrant that no longer exist in the database.
        
        This is called after a product sync to clean up deleted products.
        
        Args:
            agent_id: Agent ID
            tool_slug: Tool slug
            
        Returns:
            Removal statistics
        """
        from services.rag.retrieval_engine import RetrievalEngine
        from qdrant_client.http import models as qmodels
        
        session = self._get_session()
        
        try:
            # Get agent and RAG config
            agent = session.query(Agent).filter(Agent.id == agent_id).first()
            if not agent or not agent.rag_config_id:
                return {"success": False, "error": "Agent has no RAG configuration"}
            
            rag_config = session.query(RagConfig).filter(RagConfig.id == agent.rag_config_id).first()
            if not rag_config:
                return {"success": False, "error": "RAG configuration not found"}
            
            # Get agent tool
            agent_tool = session.query(AgentTool).filter(
                and_(
                    AgentTool.agent_id == agent_id,
                    AgentTool.tool_slug == tool_slug,
                )
            ).first()
            
            if not agent_tool:
                return {"success": False, "error": "Agent tool not found"}
            
            # Get all Qdrant point IDs for products that still exist
            existing_point_ids = set()
            for product in session.query(Product).filter(
                and_(
                    Product.agent_tool_id == agent_tool.id,
                    Product.qdrant_point_id.isnot(None),
                )
            ).all():
                existing_point_ids.add(product.qdrant_point_id)
            
            # Initialize engine
            provider_config = rag_config.provider_config or {}
            collection_name = provider_config.get("collection_name", "stimm_knowledge")
            
            engine = RetrievalEngine(
                collection_name=collection_name,
                embed_model_name=provider_config.get("embedding_model"),
                openai_api_key=provider_config.get("openai_api_key"),
            )
            
            source = f"product_sync_{agent_id}"
            
            # Get all points from Qdrant for this source
            # Then delete any that aren't in our existing set
            try:
                # Scroll through all points with this source
                points_to_delete = []
                offset = None
                
                while True:
                    results, offset = engine.client.scroll(
                        collection_name=collection_name,
                        scroll_filter=qmodels.Filter(
                            must=[
                                qmodels.FieldCondition(
                                    key="source",
                                    match=qmodels.MatchValue(value=source),
                                ),
                            ]
                        ),
                        limit=100,
                        offset=offset,
                        with_payload=False,
                        with_vectors=False,
                    )
                    
                    for point in results:
                        if str(point.id) not in existing_point_ids:
                            points_to_delete.append(point.id)
                    
                    if offset is None:
                        break
                
                # Delete orphaned points
                if points_to_delete:
                    engine.client.delete(
                        collection_name=collection_name,
                        points_selector=qmodels.PointIdsList(points=points_to_delete),
                    )
                    logger.info(f"Deleted {len(points_to_delete)} orphaned points from Qdrant")
                
                return {
                    "success": True,
                    "deleted_points": len(points_to_delete),
                }
                
            except Exception as e:
                logger.warning(f"Could not clean up deleted products: {e}")
                return {
                    "success": True,
                    "deleted_points": 0,
                    "warning": str(e),
                }
                
        finally:
            if self.db_session is None:
                session.close()

    def get_index_stats(self, agent_id: UUID, tool_slug: str = "product_stock") -> Dict[str, Any]:
        """
        Get RAG indexing statistics for an agent.
        
        Args:
            agent_id: Agent ID
            tool_slug: Tool slug
            
        Returns:
            Dictionary with indexing statistics
        """
        session = self._get_session()
        
        try:
            # Get agent tool
            agent_tool = session.query(AgentTool).filter(
                and_(
                    AgentTool.agent_id == agent_id,
                    AgentTool.tool_slug == tool_slug,
                )
            ).first()
            
            if not agent_tool:
                return {"error": "Agent tool not found"}
            
            total = session.query(Product).filter(
                Product.agent_tool_id == agent_tool.id
            ).count()
            
            indexed = session.query(Product).filter(
                and_(
                    Product.agent_tool_id == agent_tool.id,
                    Product.rag_indexed == True,
                )
            ).count()
            
            pending = total - indexed
            
            last_indexed = session.query(Product).filter(
                and_(
                    Product.agent_tool_id == agent_tool.id,
                    Product.rag_indexed == True,
                )
            ).order_by(Product.rag_indexed_at.desc()).first()
            
            return {
                "total_products": total,
                "indexed_products": indexed,
                "pending_indexing": pending,
                "last_indexed_at": last_indexed.rag_indexed_at.isoformat() if last_indexed and last_indexed.rag_indexed_at else None,
            }
            
        finally:
            if self.db_session is None:
                session.close()


# Global instance
_product_rag_manager: Optional[ProductRagManager] = None


def get_product_rag_manager() -> ProductRagManager:
    """Get the global product RAG manager instance."""
    global _product_rag_manager
    if _product_rag_manager is None:
        _product_rag_manager = ProductRagManager()
    return _product_rag_manager
