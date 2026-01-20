"""
WooCommerce Order Lookup Integration

Provides order lookup functionality via the WooCommerce REST API.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import BaseOrderLookupIntegration, OrderItem, OrderLookupResult

logger = logging.getLogger(__name__)


class WooCommerceOrderLookup(BaseOrderLookupIntegration):
    """
    WooCommerce order lookup integration using the REST API.

    Configuration:
    - store_url: WooCommerce store URL (e.g., https://mystore.com)
    - consumer_key: WooCommerce REST API consumer key
    - consumer_secret: WooCommerce REST API consumer secret
    """

    @classmethod
    def get_expected_properties(cls) -> List[str]:
        return ["store_url", "consumer_key", "consumer_secret"]

    @classmethod
    def get_field_definitions(cls) -> Dict[str, Dict[str, Any]]:
        return {
            "store_url": {
                "type": "text",
                "label": "Store URL",
                "required": True,
                "description": "Your WooCommerce store URL (e.g., https://mystore.com)",
            },
            "consumer_key": {
                "type": "text",
                "label": "Consumer Key",
                "required": True,
                "description": "WooCommerce REST API consumer key (starts with ck_)",
            },
            "consumer_secret": {
                "type": "password",
                "label": "Consumer Secret",
                "required": True,
                "description": "WooCommerce REST API consumer secret (starts with cs_)",
            },
        }

    def _get_api_url(self, endpoint: str) -> str:
        """Build the full API URL."""
        store_url = self.config["store_url"].rstrip("/")
        return f"{store_url}/wp-json/wc/v3/{endpoint}"

    def _get_auth(self) -> tuple:
        """Get authentication tuple for requests."""
        return (self.config["consumer_key"], self.config["consumer_secret"])

    def _parse_order(self, order_data: Dict[str, Any]) -> OrderLookupResult:
        """Parse WooCommerce order data into OrderLookupResult."""
        # Parse items
        items = []
        for item in order_data.get("line_items", []):
            items.append(OrderItem(
                name=item.get("name", "Unknown"),
                quantity=item.get("quantity", 1),
                price=float(item.get("total", 0)),
                sku=item.get("sku"),
            ))

        # Parse billing address
        billing = order_data.get("billing", {})
        customer_name = f"{billing.get('first_name', '')} {billing.get('last_name', '')}".strip()
        customer_email = billing.get("email")
        customer_phone = billing.get("phone")

        # Parse shipping address
        shipping = order_data.get("shipping", {})
        shipping_parts = [
            shipping.get("address_1", ""),
            shipping.get("address_2", ""),
            shipping.get("city", ""),
            shipping.get("state", ""),
            shipping.get("postcode", ""),
            shipping.get("country", ""),
        ]
        shipping_address = ", ".join(p for p in shipping_parts if p)

        # Parse dates
        created_at = None
        if order_data.get("date_created"):
            try:
                created_at = datetime.fromisoformat(
                    order_data["date_created"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        # Map WooCommerce status to human-readable
        status_map = {
            "pending": "Pending Payment",
            "processing": "Processing",
            "on-hold": "On Hold",
            "completed": "Completed",
            "cancelled": "Cancelled",
            "refunded": "Refunded",
            "failed": "Failed",
            "trash": "Deleted",
        }
        status = status_map.get(order_data.get("status", ""), order_data.get("status", "Unknown"))

        return OrderLookupResult(
            order_id=str(order_data.get("id", order_data.get("number", ""))),
            status=status,
            customer_email=customer_email,
            customer_phone=customer_phone,
            customer_name=customer_name or None,
            total=float(order_data.get("total", 0)),
            currency=order_data.get("currency", "USD"),
            created_at=created_at,
            shipping_address=shipping_address or None,
            items=items,
        )

    async def lookup_by_order_number(
        self,
        order_number: str,
    ) -> Optional[OrderLookupResult]:
        """Look up an order by its order number."""
        session = await self._get_session()
        
        try:
            # WooCommerce order ID is the order number
            url = self._get_api_url(f"orders/{order_number}")
            auth = self._get_auth()
            
            async with session.get(url, auth=aiohttp.BasicAuth(*auth)) as response:
                if response.status == 404:
                    return None
                
                response.raise_for_status()
                order_data = await response.json()
                return self._parse_order(order_data)
                
        except Exception as e:
            logger.error(f"Error looking up WooCommerce order {order_number}: {e}")
            raise

    async def lookup_by_email(
        self,
        email: str,
        limit: int = 5,
    ) -> List[OrderLookupResult]:
        """Look up orders by customer email."""
        session = await self._get_session()
        
        try:
            url = self._get_api_url("orders")
            params = {
                "search": email,
                "per_page": limit,
                "orderby": "date",
                "order": "desc",
            }
            auth = self._get_auth()
            
            async with session.get(url, auth=aiohttp.BasicAuth(*auth), params=params) as response:
                response.raise_for_status()
                orders_data = await response.json()
                
                # Filter to only orders matching the email exactly
                results = []
                for order_data in orders_data:
                    billing = order_data.get("billing", {})
                    if billing.get("email", "").lower() == email.lower():
                        results.append(self._parse_order(order_data))
                
                return results
                
        except Exception as e:
            logger.error(f"Error looking up WooCommerce orders for {email}: {e}")
            raise


# Need to import aiohttp for BasicAuth
import aiohttp
