"""
Base Order Lookup Integration

Abstract base class for order lookup integrations.
All order lookup integrations (WooCommerce, Shopify, etc.) must inherit from this class.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp


@dataclass
class OrderItem:
    """Represents an item in an order."""

    name: str
    quantity: int
    price: Optional[float] = None
    sku: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "name": self.name,
            "quantity": self.quantity,
        }
        if self.price is not None:
            result["price"] = self.price
        if self.sku:
            result["sku"] = self.sku
        return result


@dataclass
class OrderLookupResult:
    """Standardized order lookup result."""

    order_id: str
    status: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_name: Optional[str] = None
    total: Optional[float] = None
    currency: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    shipping_address: Optional[str] = None
    tracking_number: Optional[str] = None
    tracking_url: Optional[str] = None
    items: List[OrderItem] = field(default_factory=list)
    extra_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for LLM response."""
        result = {
            "order_id": self.order_id,
            "status": self.status,
        }
        if self.customer_name:
            result["customer_name"] = self.customer_name
        if self.customer_email:
            result["customer_email"] = self.customer_email
        if self.total is not None:
            result["total"] = self.total
        if self.currency:
            result["currency"] = self.currency
        if self.created_at:
            result["created_at"] = self.created_at.isoformat()
        if self.shipping_address:
            result["shipping_address"] = self.shipping_address
        if self.tracking_number:
            result["tracking_number"] = self.tracking_number
        if self.tracking_url:
            result["tracking_url"] = self.tracking_url
        if self.items:
            result["items"] = [item.to_dict() for item in self.items]
        return result
    
    def verify_customer(self, email: Optional[str] = None, phone: Optional[str] = None) -> bool:
        """
        Verify if the provided email or phone matches the order's customer info.
        
        Args:
            email: Email to verify against
            phone: Phone to verify against (digits only)
            
        Returns:
            True if at least one identifier matches
        """
        if email and self.customer_email:
            if email.lower().strip() == self.customer_email.lower().strip():
                return True
        
        if phone and self.customer_phone:
            # Normalize phones to digits only for comparison
            order_phone_digits = ''.join(filter(str.isdigit, self.customer_phone))
            provided_phone_digits = ''.join(filter(str.isdigit, phone))
            # Match if last 10 digits are the same (handles country codes)
            if order_phone_digits[-10:] == provided_phone_digits[-10:] and len(provided_phone_digits) >= 10:
                return True
        
        return False


class BaseOrderLookupIntegration(ABC):
    """
    Abstract base class for order lookup integrations.

    All order lookup integrations must implement:
    - lookup_by_order_number(): Look up order by order number
    - lookup_by_email(): Look up orders by customer email
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
    async def lookup_by_order_number(
        self,
        order_number: str,
    ) -> Optional[OrderLookupResult]:
        """
        Look up an order by its order number.

        Args:
            order_number: The order number/ID to look up

        Returns:
            OrderLookupResult if found, None otherwise
        """
        pass

    @abstractmethod
    async def lookup_by_email(
        self,
        email: str,
        limit: int = 5,
    ) -> List[OrderLookupResult]:
        """
        Look up orders by customer email.

        Args:
            email: Customer email address
            limit: Maximum number of orders to return

        Returns:
            List of OrderLookupResult objects
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
        Requires order_number AND at least one customer identifier (email or phone)
        for verification purposes.

        Args:
            parameters: Tool parameters from LLM function call

        Returns:
            Tool execution result as a dictionary
        """
        self._validate_config()

        order_number = parameters.get("order_number")
        customer_email = parameters.get("customer_email")
        customer_phone = parameters.get("customer_phone")

        try:
            if order_number:
                # Look up by order number
                result = await self.lookup_by_order_number(order_number)
                if result:
                    # Verify customer identity if we have identifiers
                    if customer_email or customer_phone:
                        if result.verify_customer(email=customer_email, phone=customer_phone):
                            return {
                                "success": True,
                                "order": result.to_dict(),
                                "found": True,
                                "verified": True,
                            }
                        else:
                            return {
                                "success": True,
                                "found": True,
                                "verified": False,
                                "message": f"Order {order_number} found but the provided email/phone does not match our records. Please verify your information.",
                            }
                    else:
                        # No verification info provided - ask for it
                        return {
                            "success": True,
                            "found": True,
                            "verified": False,
                            "message": f"Order {order_number} found. For security, please provide your email address or phone number to verify your identity.",
                        }
                else:
                    return {
                        "success": True,
                        "found": False,
                        "message": f"No order found with number {order_number}",
                    }
            elif customer_email:
                # Look up by email only (list recent orders)
                results = await self.lookup_by_email(customer_email)
                return {
                    "success": True,
                    "orders": [r.to_dict() for r in results],
                    "count": len(results),
                }
            else:
                return {
                    "success": False,
                    "error": "Order number is required. Please also provide your email or phone number for verification.",
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
