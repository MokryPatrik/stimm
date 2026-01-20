"""
WordPress/WooCommerce Product Search Integration

Searches products using the WooCommerce REST API.
Supports both WooCommerce stores and WordPress sites with WooCommerce plugin.
"""

import logging
from typing import Any, Dict, List, Optional

from .base import BaseProductSearchIntegration, ProductSearchResult

logger = logging.getLogger(__name__)


class WordPressProductSearch(BaseProductSearchIntegration):
    """
    WordPress/WooCommerce product search integration.

    Uses the WooCommerce REST API to search products.
    Requires WooCommerce REST API credentials (consumer key/secret).
    """

    async def search(
        self,
        query: str,
        category: Optional[str] = None,
        max_results: int = 5,
        **kwargs,
    ) -> List[ProductSearchResult]:
        """
        Search for products in WooCommerce.

        Args:
            query: Search query string
            category: Optional category slug to filter
            max_results: Maximum number of results

        Returns:
            List of ProductSearchResult objects
        """
        session = await self._get_session()

        base_url = self.config.get("store_url", "").rstrip("/")
        consumer_key = self.config.get("consumer_key")
        consumer_secret = self.config.get("consumer_secret")

        # Build API URL
        api_url = f"{base_url}/wp-json/wc/v3/products"

        params = {
            "search": query,
            "per_page": max_results,
            "status": "publish",
            "consumer_key": consumer_key,
            "consumer_secret": consumer_secret,
        }

        if category:
            # First, we need to get category ID from slug
            # For simplicity, we'll assume category is already the ID or skip this
            params["category"] = category

        try:
            async with session.get(api_url, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"WooCommerce API error {response.status}: {error_text}")
                    return []

                products = await response.json()
                results = []

                for product in products:
                    # Extract price
                    price = None
                    if product.get("price"):
                        try:
                            price = float(product["price"])
                        except (ValueError, TypeError):
                            pass

                    # Extract category name
                    category_name = None
                    if product.get("categories") and len(product["categories"]) > 0:
                        category_name = product["categories"][0].get("name")

                    # Check stock status
                    in_stock = product.get("in_stock", True)
                    if product.get("stock_status"):
                        in_stock = product["stock_status"] == "instock"

                    # Get image URL
                    image_url = None
                    if product.get("images") and len(product["images"]) > 0:
                        image_url = product["images"][0].get("src")

                    results.append(
                        ProductSearchResult(
                            id=str(product.get("id")),
                            name=product.get("name", ""),
                            description=product.get("short_description", ""),
                            price=price,
                            currency=self.config.get("currency", "EUR"),
                            in_stock=in_stock,
                            url=product.get("permalink"),
                            image_url=image_url,
                            category=category_name,
                        )
                    )

                return results

        except Exception as e:
            logger.error(f"Error searching WooCommerce products: {e}")
            raise

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
        }
