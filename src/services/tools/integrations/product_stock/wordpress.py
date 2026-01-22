"""
WordPress/WooCommerce Product Stock Integration

Checks real-time product stock/availability using the WooCommerce REST API.
For general product information, use RAG retrieval instead.
"""

import logging
from typing import Any, Dict, List, Optional

from .base import BaseProductStockIntegration, ProductStockResult, ProductSyncResult

logger = logging.getLogger(__name__)


class WordPressProductStock(BaseProductStockIntegration):
    """
    WordPress/WooCommerce product stock integration.

    Uses the WooCommerce REST API to check real-time stock levels.
    Requires WooCommerce REST API credentials (consumer key/secret).
    """

    async def check_stock(
        self,
        product_name: str,
        product_id: Optional[str] = None,
    ) -> List[ProductStockResult]:
        """
        Check stock for a product in WooCommerce.

        Args:
            product_name: Product name to search for
            product_id: Optional product ID for direct lookup

        Returns:
            List of ProductStockResult objects
        """
        session = await self._get_session()

        base_url = self.config.get("store_url", "").rstrip("/")
        consumer_key = self.config.get("consumer_key")
        consumer_secret = self.config.get("consumer_secret")

        # Build API URL
        api_url = f"{base_url}/wp-json/wc/v3/products"

        # If we have a product ID, fetch directly
        if product_id:
            api_url = f"{api_url}/{product_id}"
            params = {
                "consumer_key": consumer_key,
                "consumer_secret": consumer_secret,
            }
            try:
                async with session.get(api_url, params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"WooCommerce API error {response.status}: {error_text}")
                        return []

                    product = await response.json()
                    return [self._parse_stock(product)]

            except Exception as e:
                logger.error(f"Error fetching WooCommerce product by ID: {e}")
                raise
        else:
            # Search by name
            params = {
                "search": product_name,
                "per_page": 5,
                "status": "publish",
                "consumer_key": consumer_key,
                "consumer_secret": consumer_secret,
            }

            try:
                async with session.get(api_url, params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"WooCommerce API error {response.status}: {error_text}")
                        return []

                    products = await response.json()
                    return [self._parse_stock(p) for p in products]

            except Exception as e:
                logger.error(f"Error searching WooCommerce products: {e}")
                raise

    async def fetch_all_products(
        self, 
        per_page: int = 100,
        modified_after: Optional[str] = None,
    ) -> List[ProductSyncResult]:
        """
        Fetch products from WooCommerce for RAG sync.

        Args:
            per_page: Number of products per page (max 100)
            modified_after: ISO timestamp - only fetch products modified after this time

        Returns:
            List of ProductSyncResult objects for database sync
        """
        session = await self._get_session()

        base_url = self.config.get("store_url", "").rstrip("/")
        consumer_key = self.config.get("consumer_key")
        consumer_secret = self.config.get("consumer_secret")
        currency = self.config.get("currency", "EUR")
        
        # Get max products limit from config (0 or None means no limit)
        max_products_raw = self.config.get("max_products", 0)
        try:
            max_products = int(max_products_raw) if max_products_raw else 0
        except (ValueError, TypeError):
            max_products = 0
        
        if max_products:
            logger.info(f"Max products limit set to {max_products}")
        
        if modified_after:
            logger.info(f"Incremental sync: fetching products modified after {modified_after}")

        api_url = f"{base_url}/wp-json/wc/v3/products"
        all_products = []
        page = 1

        while True:
            params = {
                "per_page": min(per_page, 100),
                "page": page,
                "status": "publish",
                "consumer_key": consumer_key,
                "consumer_secret": consumer_secret,
            }
            
            # Add modified_after filter for incremental sync
            if modified_after:
                params["modified_after"] = modified_after

            try:
                async with session.get(api_url, params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"WooCommerce API error {response.status}: {error_text}")
                        break

                    products = await response.json()
                    
                    if not products:
                        break
                    
                    # Convert to ProductSyncResult objects
                    parsed = [self._parse_for_sync(p, currency) for p in products]
                    
                    # Check if we need to limit products
                    if max_products and len(all_products) + len(parsed) >= max_products:
                        remaining = max_products - len(all_products)
                        all_products.extend(parsed[:remaining])
                        logger.info(f"Reached max products limit ({max_products}). Stopping fetch.")
                        break
                    
                    all_products.extend(parsed)
                    logger.info(f"Fetched page {page}: {len(products)} products (total: {len(all_products)})")
                    
                    # Check if we got fewer products than requested (last page)
                    if len(products) < per_page:
                        break
                    
                    page += 1

            except Exception as e:
                logger.error(f"Error fetching WooCommerce products page {page}: {e}")
                break

        return all_products

    def _parse_for_sync(self, product: Dict[str, Any], currency: str) -> ProductSyncResult:
        """Parse WooCommerce API response into ProductSyncResult for sync."""
        # Check stock status
        in_stock = product.get("in_stock", True)
        if product.get("stock_status"):
            in_stock = product["stock_status"] == "instock"
        
        # Get price
        price = None
        price_str = product.get("price")
        if price_str:
            try:
                price = float(price_str)
            except (ValueError, TypeError):
                pass
        
        # Get category
        categories = product.get("categories", [])
        category = categories[0].get("name") if categories else None
        
        # Get primary image
        images = product.get("images", [])
        image_url = images[0].get("src") if images else None
        
        # Build extra data
        extra_data = {
            "sku": product.get("sku"),
            "long_description": product.get("description", ""),
            "on_sale": product.get("on_sale", False),
            "regular_price": product.get("regular_price"),
            "sale_price": product.get("sale_price"),
            "stock_quantity": product.get("stock_quantity"),
            "attributes": product.get("attributes", []),
            "tags": [t.get("name") for t in product.get("tags", [])],
            "weight": product.get("weight"),
            "dimensions": product.get("dimensions"),
        }
        
        return ProductSyncResult(
            id=str(product.get("id")),
            name=product.get("name", ""),
            description=product.get("short_description", ""),
            price=price,
            currency=currency,
            category=category,
            url=product.get("permalink"),
            image_url=image_url,
            in_stock=in_stock,
            extra_data=extra_data,
        )

    def _parse_stock(self, product: Dict[str, Any]) -> ProductStockResult:
        """Parse WooCommerce API response into ProductStockResult object."""
        # Check stock status
        in_stock = product.get("in_stock", True)
        if product.get("stock_status"):
            in_stock = product["stock_status"] == "instock"

        # Get stock quantity
        stock_quantity = product.get("stock_quantity")
        
        # Determine availability message
        if not in_stock:
            availability = "Out of stock"
        elif stock_quantity is not None:
            if stock_quantity > 10:
                availability = "In stock"
            elif stock_quantity > 0:
                availability = f"Low stock ({stock_quantity} left)"
            else:
                availability = "Out of stock"
        else:
            availability = "In stock" if in_stock else "Out of stock"

        return ProductStockResult(
            id=str(product.get("id")),
            name=product.get("name", ""),
            in_stock=in_stock,
            stock_quantity=stock_quantity,
            availability=availability,
            backorders_allowed=product.get("backorders_allowed", False),
        )

    @classmethod
    def get_expected_properties(cls) -> List[str]:
        """Get required configuration properties."""
        return ["store_url", "consumer_key", "consumer_secret"]

    @classmethod
    def get_field_definitions(cls) -> Dict[str, Dict[str, Any]]:
        """Get field definitions for UI configuration."""
        return {
            "store_url": {
                "type": "text",
                "label": "Store URL",
                "required": True,
                "description": "Your WooCommerce store URL (e.g., https://mystore.com)",
                "placeholder": "https://mystore.com",
            },
            "consumer_key": {
                "type": "password",
                "label": "Consumer Key",
                "required": True,
                "description": "WooCommerce REST API Consumer Key",
            },
            "consumer_secret": {
                "type": "password",
                "label": "Consumer Secret",
                "required": True,
                "description": "WooCommerce REST API Consumer Secret",
            },
            "currency": {
                "type": "text",
                "label": "Currency",
                "required": False,
                "description": "Currency code for prices (default: EUR)",
                "default": "EUR",
            },
            "use_as_rag": {
                "type": "boolean",
                "label": "Sync to RAG",
                "required": False,
                "description": "Automatically sync products to RAG knowledge base",
                "default": False,
            },
            "sync_interval_hours": {
                "type": "number",
                "label": "Sync Interval (hours)",
                "required": False,
                "description": "How often to sync products (default: 24 hours)",
                "default": 24,
            },
            "max_products": {
                "type": "number",
                "label": "Max Products",
                "required": False,
                "description": "Maximum number of products to sync (0 = no limit). Useful for testing.",
                "default": 0,
            },
        }
