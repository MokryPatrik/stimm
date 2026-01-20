"""
Tool Registry System

This module provides a registry for discovering and managing tool integration classes.
It mirrors the ProviderRegistry pattern used for LLM, TTS, and STT providers.
"""

import importlib
import logging
from typing import Any, Dict, List, Optional, Type

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Registry for discovering and managing tool integration classes.

    This class provides dynamic discovery of tool implementations
    and access to their metadata including expected configuration properties.
    """

    # Tool slug to module mapping
    TOOL_MODULES = {
        "product_search": "services.tools.integrations.product_search",
        "order_lookup": "services.tools.integrations.order_lookup",
        "calendar": "services.tools.integrations.calendar",
        "custom_api": "services.tools.integrations.custom_api",
    }

    # Integration slug to class name mapping for each tool
    INTEGRATION_CLASSES = {
        "product_search": {
            "wordpress": "wordpress.WordPressProductSearch",
            "shopify": "shopify.ShopifyProductSearch",
            "woocommerce": "woocommerce.WooCommerceProductSearch",
            "custom_api": "custom_api.CustomAPIProductSearch",
        },
        "order_lookup": {
            "shopify": "shopify.ShopifyOrderLookup",
            "woocommerce": "woocommerce.WooCommerceOrderLookup",
        },
        "calendar": {
            "google_calendar": "google_calendar.GoogleCalendarIntegration",
            "outlook": "outlook.OutlookCalendarIntegration",
        },
        "custom_api": {
            "rest": "rest.RestAPIIntegration",
            "graphql": "graphql.GraphQLIntegration",
        },
    }

    # Tool definitions with OpenAI function calling schema format
    TOOL_DEFINITIONS = {
        "product_search": {
            "name": "product_search",
            "description": "Search for products in the catalog by name, category, or other attributes. Use this when the user asks about products, availability, or prices.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to find products (product name, keywords, or description)"
                    },
                    "category": {
                        "type": "string",
                        "description": "Optional category to filter products"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        },
        "order_lookup": {
            "name": "order_lookup",
            "description": "Look up order status and details. Requires order number AND a customer identifier (email or phone) for verification. If the caller's phone number is known from the call context, use that automatically.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_number": {
                        "type": "string",
                        "description": "The order number to look up"
                    },
                    "customer_email": {
                        "type": "string",
                        "description": "Customer email address for verification"
                    },
                    "customer_phone": {
                        "type": "string",
                        "description": "Customer phone number for verification (digits only, e.g., '5551234567')"
                    }
                },
                "required": ["order_number"]
            }
        },
        "calendar": {
            "name": "calendar",
            "description": "Check availability and schedule appointments. Use this when the user wants to book a meeting or check available times.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["check_availability", "book_appointment", "cancel_appointment"],
                        "description": "The calendar action to perform"
                    },
                    "date": {
                        "type": "string",
                        "description": "Date for the action (ISO 8601 format)"
                    },
                    "time": {
                        "type": "string",
                        "description": "Time for the action (HH:MM format)"
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "description": "Duration of the appointment in minutes",
                        "default": 30
                    }
                },
                "required": ["action"]
            }
        },
        "custom_api": {
            "name": "custom_api",
            "description": "Call a custom API endpoint to retrieve or submit data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "endpoint": {
                        "type": "string",
                        "description": "API endpoint path to call"
                    },
                    "method": {
                        "type": "string",
                        "enum": ["GET", "POST", "PUT", "DELETE"],
                        "description": "HTTP method to use"
                    },
                    "data": {
                        "type": "object",
                        "description": "Data to send with the request"
                    }
                },
                "required": ["endpoint"]
            }
        }
    }

    def __init__(self):
        self._cache: Dict[str, Type] = {}

    def get_integration_class(self, tool_slug: str, integration_slug: str) -> Optional[Type]:
        """
        Get integration class for a given tool and integration.

        Args:
            tool_slug: Slug of the tool (e.g., 'product_search')
            integration_slug: Slug of the integration (e.g., 'wordpress')

        Returns:
            Integration class or None if not found
        """
        cache_key = f"{tool_slug}.{integration_slug}"

        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            module_name = self.TOOL_MODULES.get(tool_slug)
            class_path = self.INTEGRATION_CLASSES.get(tool_slug, {}).get(integration_slug)

            if not module_name or not class_path:
                logger.warning(f"Integration not found: {tool_slug}.{integration_slug}")
                return None

            # Handle submodule imports (e.g., "wordpress.WordPressProductSearch")
            if "." in class_path:
                submodule_name, class_name = class_path.split(".", 1)
                full_module_name = f"{module_name}.{submodule_name}"
            else:
                full_module_name = module_name
                class_name = class_path

            # Import module and get class
            module = importlib.import_module(full_module_name)
            integration_class = getattr(module, class_name, None)

            if integration_class:
                self._cache[cache_key] = integration_class
                return integration_class
            else:
                logger.warning(f"Integration class {class_name} not found in module {full_module_name}")
                return None

        except ImportError as e:
            logger.warning(f"Failed to import integration module for {tool_slug}.{integration_slug}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error loading integration {tool_slug}.{integration_slug}: {e}")
            return None

    def get_tool_definition(self, tool_slug: str) -> Optional[Dict[str, Any]]:
        """
        Get the OpenAI function calling definition for a tool.

        Args:
            tool_slug: Slug of the tool

        Returns:
            Tool definition dict or None if not found
        """
        return self.TOOL_DEFINITIONS.get(tool_slug)

    def get_expected_properties(self, tool_slug: str, integration_slug: str) -> List[str]:
        """
        Get expected configuration properties for an integration.

        Args:
            tool_slug: Slug of the tool
            integration_slug: Slug of the integration

        Returns:
            List of expected property names
        """
        integration_class = self.get_integration_class(tool_slug, integration_slug)

        if not integration_class:
            logger.warning(f"Cannot get expected properties for unknown integration: {tool_slug}.{integration_slug}")
            return []

        try:
            if hasattr(integration_class, "get_expected_properties"):
                return integration_class.get_expected_properties()
            else:
                logger.warning(f"Integration {tool_slug}.{integration_slug} does not implement get_expected_properties()")
                return []

        except Exception as e:
            logger.error(f"Error getting expected properties for {tool_slug}.{integration_slug}: {e}")
            return []

    def get_field_definitions(self, tool_slug: str, integration_slug: str) -> Dict[str, Dict[str, Any]]:
        """
        Get field definitions for an integration's configuration.

        Args:
            tool_slug: Slug of the tool
            integration_slug: Slug of the integration

        Returns:
            Dictionary of field definitions with type, label, and required status
        """
        integration_class = self.get_integration_class(tool_slug, integration_slug)

        if not integration_class:
            logger.warning(f"Cannot get field definitions for unknown integration: {tool_slug}.{integration_slug}")
            return {}

        try:
            if hasattr(integration_class, "get_field_definitions"):
                return integration_class.get_field_definitions()
            else:
                # Fallback to basic field definitions from expected properties
                expected_properties = self.get_expected_properties(tool_slug, integration_slug)
                return {
                    prop: {
                        "type": "text",
                        "label": prop.replace("_", " ").title(),
                        "required": True,
                    }
                    for prop in expected_properties
                }

        except Exception as e:
            logger.error(f"Error getting field definitions for {tool_slug}.{integration_slug}: {e}")
            return {}

    def get_available_tools(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all available tools with their integrations and metadata.

        Returns:
            Dictionary with tool slugs as keys and metadata as values
        """
        result = {}

        for tool_slug, tool_def in self.TOOL_DEFINITIONS.items():
            integrations = []
            field_definitions = {}

            for integration_slug in self.INTEGRATION_CLASSES.get(tool_slug, {}).keys():
                # Get integration label (human-readable name)
                label = integration_slug.replace("_", " ").title()
                integrations.append({"value": integration_slug, "label": label})

                # Get field definitions for this integration
                integration_fields = self.get_field_definitions(tool_slug, integration_slug)
                field_definitions[integration_slug] = integration_fields

            result[tool_slug] = {
                "name": tool_def["name"],
                "description": tool_def["description"],
                "parameters": tool_def["parameters"],
                "integrations": integrations,
                "field_definitions": field_definitions,
            }

        return result

    def format_tools_for_llm(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format tool definitions for OpenAI-compatible function calling.

        Args:
            tools: List of tool configurations from agent_tools

        Returns:
            List of tool definitions in OpenAI function calling format
        """
        formatted_tools = []

        for tool in tools:
            tool_slug = tool.get("tool_slug")
            tool_def = self.get_tool_definition(tool_slug)

            if tool_def:
                formatted_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool_def["name"],
                        "description": tool_def["description"],
                        "parameters": tool_def["parameters"],
                    }
                })

        return formatted_tools

    def build_system_prompt_tools_section(self, tools: List[Dict[str, Any]]) -> str:
        """
        Build a tools description section to append to system prompts.

        Args:
            tools: List of tool configurations from agent_tools

        Returns:
            String describing available tools for the system prompt
        """
        if not tools:
            return ""

        lines = ["\n## Available Tools\n", "You have access to the following tools:\n"]

        for tool in tools:
            tool_slug = tool.get("tool_slug")
            tool_def = self.get_tool_definition(tool_slug)

            if tool_def:
                lines.append(f"- **{tool_def['name']}**: {tool_def['description']}")

        lines.append("\nWhen you need to use a tool, respond with a function call in the appropriate format.")

        return "\n".join(lines)


# Global registry instance
_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance."""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
    return _tool_registry
