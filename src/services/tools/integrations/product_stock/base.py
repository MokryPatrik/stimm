"""
Base Product Stock Integration

Abstract base class for product stock/availability integrations.
All product stock integrations (WordPress, Shopify, etc.) must inherit from this class.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import aiohttp


@dataclass
class ProductStockResult:
    """Standardized product stock result."""

    id: str
    name: str
    in_stock: bool
    stock_quantity: Optional[int] = None
    availability: Optional[str] = None  # e.g., "In stock", "Low stock (3 left)", "Out of stock"
    backorders_allowed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for LLM response."""
        return {
            "id": self.id,
            "name": self.name,
            "in_stock": self.in_stock,
            "stock_quantity": self.stock_quantity,
            "availability": self.availability or ("In stock" if self.in_stock else "Out of stock"),
            "backorders_allowed": self.backorders_allowed,
        }


@dataclass
class ProductSyncResult:
    """
    Standardized product result for sync/RAG indexing.
    
    This contains all product information needed for database storage
    and RAG embedding (not just stock info).
    """

    id: str
    name: str
    description: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    category: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    in_stock: bool = True
    extra_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "currency": self.currency,
            "category": self.category,
            "url": self.url,
            "image_url": self.image_url,
            "in_stock": self.in_stock,
            "extra_data": self.extra_data,
        }


class BaseProductStockIntegration(ABC):
    """
    Abstract base class for product stock integrations.

    All product stock integrations must implement:
    - check_stock(): Check stock for a product
    - get_expected_properties(): Return list of required config properties
    - get_field_definitions(): Return field metadata for UI
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the integration with configuration.

        Args:
            config: Integration-specific configuration (API keys, URLs, etc.)
        """
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Close the HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None

    @abstractmethod
    async def check_stock(
        self,
        product_name: str,
        product_id: Optional[str] = None,
    ) -> List[ProductStockResult]:
        """
        Check stock for a product.

        Args:
            product_name: Product name to search for
            product_id: Optional product ID for direct lookup

        Returns:
            List of ProductStockResult objects
        """
        pass

    @classmethod
    @abstractmethod
    def get_expected_properties(cls) -> List[str]:
        """
        Get the list of expected configuration properties.

        Returns:
            List of property names that this integration expects
        """
        pass

    @classmethod
    @abstractmethod
    def get_field_definitions(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get the field definitions for this integration's configuration.

        Returns:
            Dictionary mapping field names to field metadata:
            - type: Field type (text, password, select, etc.)
            - label: Human-readable label
            - required: Whether the field is required
            - description: Help text for the field
        """
        pass

    def _validate_config(self):
        """Validate that required configuration is present."""
        expected = self.get_expected_properties()
        for prop in expected:
            if not self.config.get(prop):
                raise ValueError(f"{self.__class__.__name__}: {prop} is required")

    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the tool with given parameters.

        This is the main entry point called by ToolExecutor.

        Args:
            parameters: Tool parameters from LLM function call

        Returns:
            Tool execution result as a dictionary
        """
        self._validate_config()

        product_name = parameters.get("product_name", "")
        product_id = parameters.get("product_id")

        try:
            results = await self.check_stock(product_name, product_id)
            
            if not results:
                return {
                    "success": True,
                    "message": f"No products found matching '{product_name}'",
                    "results": [],
                    "count": 0,
                }
            
            return {
                "success": True,
                "results": [r.to_dict() for r in results],
                "count": len(results),
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "results": [],
                "count": 0,
            }
