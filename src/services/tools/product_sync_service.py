"""
Product Sync Service - Syncs products from e-commerce to local database.

This service handles the first stage of the sync pipeline:
1. Fetch products from external source (WooCommerce, Shopify, etc.)
2. Store/update them in the local products table
3. Track changes via content_hash for incremental RAG updates

The RAG Manager then handles embedding only the changed products.
"""

import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy.orm import Session

from database import AgentTool, Product
from database.session import SessionLocal

logger = logging.getLogger(__name__)


def compute_content_hash(product_data: Dict[str, Any]) -> str:
    """
    Compute a hash of product content for change detection.
    
    Only includes fields that affect the RAG embedding.
    """
    # Fields that affect the RAG text representation
    relevant_fields = [
        product_data.get("name", ""),
        product_data.get("description", ""),
        product_data.get("long_description", ""),
        str(product_data.get("price", "")),
        product_data.get("currency", ""),
        product_data.get("category", ""),
        product_data.get("sku", ""),
        str(product_data.get("in_stock", True)),
        product_data.get("url", ""),
    ]
    
    # Include relevant extra_data fields
    extra = product_data.get("extra_data", {}) or {}
    if extra.get("on_sale"):
        relevant_fields.append(str(extra.get("regular_price", "")))
        relevant_fields.append("on_sale")
    
    for attr in extra.get("attributes", []):
        relevant_fields.append(f"{attr.get('name', '')}:{','.join(attr.get('options', []))}")
    
    content = "|".join(str(f) for f in relevant_fields)
    return hashlib.sha256(content.encode()).hexdigest()


class ProductSyncService:
    """
    Service for syncing products from e-commerce platforms to local database.
    
    This is the first stage of the sync pipeline. Products are stored in
    PostgreSQL, and changed products are flagged for RAG re-indexing.
    """

    def __init__(self, db_session: Session = None):
        self.db_session = db_session
        self._running_syncs: Dict[str, bool] = {}

    def _get_session(self) -> Session:
        """Get database session."""
        if self.db_session:
            return self.db_session
        return SessionLocal()

    def _get_sync_key(self, agent_tool_id: UUID) -> str:
        """Generate a unique key for tracking sync status."""
        return str(agent_tool_id)

    def is_sync_running(self, agent_tool_id: UUID) -> bool:
        """Check if a sync is currently running for this agent tool."""
        key = self._get_sync_key(agent_tool_id)
        return self._running_syncs.get(key, False)

    async def sync_products_to_db(
        self,
        agent_tool: AgentTool,
        products: List[Any],
    ) -> Dict[str, Any]:
        """
        Sync fetched products to the local database.
        
        Args:
            agent_tool: The agent tool configuration
            products: List of ProductSearchResult objects from the integration
            
        Returns:
            Sync statistics including new, updated, unchanged, and deleted counts
        """
        sync_key = self._get_sync_key(agent_tool.id)
        if self._running_syncs.get(sync_key, False):
            return {
                "success": True,
                "skipped": True,
                "message": "Sync already in progress",
            }
        
        self._running_syncs[sync_key] = True
        session = self._get_session()
        
        try:
            stats = {
                "new": 0,
                "updated": 0,
                "unchanged": 0,
                "deleted": 0,
                "total": len(products),
            }
            
            # Get existing products for this agent tool
            existing_products = {
                p.external_id: p
                for p in session.query(Product).filter(
                    Product.agent_tool_id == agent_tool.id
                ).all()
            }
            
            # Track which external IDs we've seen (handle duplicates from source)
            seen_external_ids = set()
            
            # De-duplicate products from source (keep last occurrence)
            products_by_id = {}
            for product in products:
                products_by_id[str(product.id)] = product
            unique_products = list(products_by_id.values())
            
            if len(unique_products) < len(products):
                logger.warning(
                    f"Source had {len(products) - len(unique_products)} duplicate products, "
                    f"keeping {len(unique_products)} unique products"
                )
            
            # Process products in batches
            batch_size = 100
            for i in range(0, len(unique_products), batch_size):
                batch = unique_products[i:i + batch_size]
                
                for product in batch:
                    external_id = str(product.id)
                    seen_external_ids.add(external_id)
                    
                    # Build product data dict
                    product_data = {
                        "name": product.name,
                        "description": product.description,
                        "long_description": product.extra_data.get("long_description") if product.extra_data else None,
                        "price": str(product.price) if product.price is not None else None,
                        "currency": product.currency,
                        "category": product.category,
                        "sku": product.extra_data.get("sku") if product.extra_data else None,
                        "url": product.url,
                        "image_url": product.image_url,
                        "in_stock": product.in_stock,
                        "extra_data": product.extra_data or {},
                    }
                    
                    content_hash = compute_content_hash(product_data)
                    
                    existing = existing_products.get(external_id)
                    
                    if existing:
                        # Check if content changed
                        if existing.content_hash != content_hash:
                            # Update existing product
                            existing.name = product_data["name"]
                            existing.description = product_data["description"]
                            existing.long_description = product_data["long_description"]
                            existing.price = product_data["price"]
                            existing.currency = product_data["currency"]
                            existing.category = product_data["category"]
                            existing.sku = product_data["sku"]
                            existing.url = product_data["url"]
                            existing.image_url = product_data["image_url"]
                            existing.in_stock = product_data["in_stock"]
                            existing.extra_data = product_data["extra_data"]
                            existing.content_hash = content_hash
                            # Mark as needing re-indexing
                            existing.rag_indexed = False
                            existing.updated_at = datetime.utcnow()
                            stats["updated"] += 1
                        else:
                            stats["unchanged"] += 1
                    else:
                        # Create new product
                        new_product = Product(
                            agent_tool_id=agent_tool.id,
                            external_id=external_id,
                            name=product_data["name"],
                            description=product_data["description"],
                            long_description=product_data["long_description"],
                            price=product_data["price"],
                            currency=product_data["currency"],
                            category=product_data["category"],
                            sku=product_data["sku"],
                            url=product_data["url"],
                            image_url=product_data["image_url"],
                            in_stock=product_data["in_stock"],
                            extra_data=product_data["extra_data"],
                            content_hash=content_hash,
                            rag_indexed=False,
                        )
                        session.add(new_product)
                        stats["new"] += 1
                
                # Commit after each batch
                session.commit()
                logger.info(f"Processed batch {i // batch_size + 1}: {min(i + batch_size, len(unique_products))}/{len(unique_products)} products")
            
            # Delete products that no longer exist in the source
            for external_id, existing in existing_products.items():
                if external_id not in seen_external_ids:
                    session.delete(existing)
                    stats["deleted"] += 1
            
            session.commit()
            
            logger.info(
                f"Product sync complete: {stats['new']} new, {stats['updated']} updated, "
                f"{stats['unchanged']} unchanged, {stats['deleted']} deleted"
            )
            
            return {
                "success": True,
                **stats,
            }
            
        except Exception as e:
            logger.error(f"Error syncing products to database: {e}")
            session.rollback()
            return {
                "success": False,
                "error": str(e),
            }
        finally:
            self._running_syncs[sync_key] = False
            if self.db_session is None:
                session.close()

    def get_products_needing_indexing(
        self,
        agent_tool_id: UUID,
        limit: int = 500,
    ) -> List[Product]:
        """
        Get products that need RAG indexing.
        
        Args:
            agent_tool_id: The agent tool ID
            limit: Maximum number of products to return
            
        Returns:
            List of Product objects needing indexing
        """
        session = self._get_session()
        try:
            return session.query(Product).filter(
                and_(
                    Product.agent_tool_id == agent_tool_id,
                    Product.rag_indexed == False,
                )
            ).limit(limit).all()
        finally:
            if self.db_session is None:
                session.close()

    def mark_products_indexed(
        self,
        product_ids: List[UUID],
        qdrant_point_ids: Dict[UUID, str],
    ) -> None:
        """
        Mark products as indexed in RAG.
        
        Args:
            product_ids: List of product IDs that were indexed
            qdrant_point_ids: Mapping of product ID to Qdrant point ID
        """
        session = self._get_session()
        try:
            now = datetime.utcnow()
            for product_id in product_ids:
                product = session.query(Product).filter(Product.id == product_id).first()
                if product:
                    product.rag_indexed = True
                    product.rag_indexed_at = now
                    product.qdrant_point_id = qdrant_point_ids.get(product_id)
            session.commit()
        finally:
            if self.db_session is None:
                session.close()

    def get_sync_stats(self, agent_tool_id: UUID) -> Dict[str, Any]:
        """
        Get sync statistics for an agent tool.
        
        Args:
            agent_tool_id: The agent tool ID
            
        Returns:
            Dictionary with sync statistics
        """
        session = self._get_session()
        try:
            total = session.query(Product).filter(
                Product.agent_tool_id == agent_tool_id
            ).count()
            
            indexed = session.query(Product).filter(
                and_(
                    Product.agent_tool_id == agent_tool_id,
                    Product.rag_indexed == True,
                )
            ).count()
            
            pending = total - indexed
            
            # Get last sync time
            last_product = session.query(Product).filter(
                Product.agent_tool_id == agent_tool_id
            ).order_by(Product.updated_at.desc()).first()
            
            last_indexed = session.query(Product).filter(
                and_(
                    Product.agent_tool_id == agent_tool_id,
                    Product.rag_indexed == True,
                )
            ).order_by(Product.rag_indexed_at.desc()).first()
            
            return {
                "total_products": total,
                "indexed_products": indexed,
                "pending_indexing": pending,
                "last_product_sync": last_product.updated_at.isoformat() if last_product else None,
                "last_rag_index": last_indexed.rag_indexed_at.isoformat() if last_indexed and last_indexed.rag_indexed_at else None,
            }
        finally:
            if self.db_session is None:
                session.close()


# Global service instance
_product_sync_service: Optional[ProductSyncService] = None


def get_product_sync_service() -> ProductSyncService:
    """Get the global product sync service instance."""
    global _product_sync_service
    if _product_sync_service is None:
        _product_sync_service = ProductSyncService()
    return _product_sync_service
