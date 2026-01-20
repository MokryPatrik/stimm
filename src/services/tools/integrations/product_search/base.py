"""
Base Product Search Integration

Abstract base class for product search integrations.
All product search integrations (WordPress, Shopify, etc.) must inherit from this class.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import aiohttp


@dataclass
class ProductSearchResult:
    """Standardized product search result."""

    id: str
    name: str
    description: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    in_stock: Optional[bool] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for LLM response."""
        result = {
            "id": self.id,
            "name": self.name,
        }
        if self.description:
            result["description"] = self.description
        if self.price is not None:
            result["price"] = self.price
        if self.currency:
            result["currency"] = self.currency
        if self.in_stock is not None:
            result["in_stock"] = self.in_stock
        if self.url:
            result["url"] = self.url
        if self.category:
            result["category"] = self.category
        return result


class BaseProductSearchIntegration(ABC):
    """
    Abstract base class for product search integrations.

    All product search integrations must implement:
    - search(): Execute a product search
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
    async def search(
        self,
        query: str,
        category: Optional[str] = None,
        max_results: int = 5,
        **kwargs,
    ) -> List[ProductSearchResult]:
        """
        Search for products.

        Args:
            query: Search query string
            category: Optional category filter
            max_results: Maximum number of results to return
            **kwargs: Additional integration-specific parameters

        Returns:
            List of ProductSearchResult objects
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

        query = parameters.get("query", "")
        category = parameters.get("category")
        max_results = parameters.get("max_results", 5)

        try:
            results = await self.search(query, category, max_results)
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
