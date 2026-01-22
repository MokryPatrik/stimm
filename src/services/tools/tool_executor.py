"""
Tool Executor

This module provides the ToolExecutor class that handles executing tool calls
from LLM responses. It manages integration instantiation, execution, and
result formatting.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from .tool_registry import ToolRegistry, get_tool_registry

logger = logging.getLogger(__name__)


class ToolExecutor:
    """
    Executor for tool calls from LLM responses.

    Handles:
    - Parsing tool calls from LLM responses
    - Instantiating appropriate integrations
    - Executing tools with parameters
    - Formatting results for LLM consumption
    """

    def __init__(self, agent_tools: List[Dict[str, Any]]):
        """
        Initialize the executor with agent's tool configurations.

        Args:
            agent_tools: List of agent tool configurations from database
                Each item should have: tool_slug, integration_slug, integration_config, is_enabled
        """
        self.agent_tools = {
            tool["tool_slug"]: tool
            for tool in agent_tools
            if tool.get("is_enabled", True)
        }
        self.registry = get_tool_registry()
        self._integration_cache: Dict[str, Any] = {}

    def get_enabled_tool_slugs(self) -> List[str]:
        """Get list of enabled tool slugs for this agent."""
        return list(self.agent_tools.keys())

    def get_tools_for_llm(self) -> List[Dict[str, Any]]:
        """
        Get tool definitions formatted for OpenAI function calling.

        Returns:
            List of tool definitions in OpenAI format
        """
        tools = []
        for tool_slug in self.agent_tools:
            tool_def = self.registry.get_tool_definition(tool_slug)
            if tool_def:
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool_def["name"],
                        "description": tool_def["description"],
                        "parameters": tool_def["parameters"],
                    }
                })
        return tools

    def _get_integration(self, tool_slug: str):
        """
        Get or create an integration instance for a tool.

        Args:
            tool_slug: The tool slug

        Returns:
            Integration instance or None if not found
        """
        if tool_slug in self._integration_cache:
            return self._integration_cache[tool_slug]

        tool_config = self.agent_tools.get(tool_slug)
        if not tool_config:
            logger.warning(f"Tool {tool_slug} not configured for this agent")
            return None

        integration_slug = tool_config.get("integration_slug")
        integration_config = tool_config.get("integration_config", {})

        integration_class = self.registry.get_integration_class(tool_slug, integration_slug)
        if not integration_class:
            logger.warning(f"Integration class not found: {tool_slug}.{integration_slug}")
            return None

        try:
            integration = integration_class(integration_config)
            self._integration_cache[tool_slug] = integration
            return integration
        except Exception as e:
            logger.error(f"Failed to instantiate integration {tool_slug}.{integration_slug}: {e}")
            return None

    async def execute_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute a single tool call.

        Args:
            tool_name: Name of the tool to execute (same as tool_slug)
            arguments: Tool arguments from LLM

        Returns:
            Tool execution result
        """
        logger.info(f"Executing tool '{tool_name}' with arguments: {arguments}")
        
        integration = self._get_integration(tool_name)
        if not integration:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' is not available",
            }

        try:
            result = await integration.execute(arguments)
            logger.info(f"Tool '{tool_name}' result: success={result.get('success')}, count={result.get('count', 'N/A')}")
            return result
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def execute_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Execute multiple tool calls (from OpenAI format).

        Args:
            tool_calls: List of tool calls in OpenAI format:
                [{"id": "...", "function": {"name": "...", "arguments": "..."}}]

        Returns:
            List of tool results with call IDs
        """
        results = []

        for tool_call in tool_calls:
            call_id = tool_call.get("id", "")
            function = tool_call.get("function", {})
            tool_name = function.get("name", "")
            arguments_str = function.get("arguments", "{}")

            # Parse arguments
            try:
                arguments = json.loads(arguments_str) if isinstance(arguments_str, str) else arguments_str
            except json.JSONDecodeError:
                arguments = {}

            # Execute the tool
            result = await self.execute_tool_call(tool_name, arguments)

            results.append({
                "tool_call_id": call_id,
                "role": "tool",
                "content": json.dumps(result),
            })

        return results

    def parse_tool_calls_from_response(
        self,
        response: Dict[str, Any],
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Parse tool calls from an OpenAI-format response.

        Args:
            response: LLM response dict

        Returns:
            List of tool calls or None if no tool calls
        """
        # Check for tool_calls in the message
        message = response.get("choices", [{}])[0].get("message", {})
        tool_calls = message.get("tool_calls")

        if tool_calls:
            return tool_calls

        return None

    def has_tool_calls(self, response: Dict[str, Any]) -> bool:
        """Check if response contains tool calls."""
        return self.parse_tool_calls_from_response(response) is not None

    async def close(self):
        """Close all cached integrations."""
        for integration in self._integration_cache.values():
            if hasattr(integration, "close"):
                try:
                    await integration.close()
                except Exception as e:
                    logger.warning(f"Error closing integration: {e}")
        self._integration_cache.clear()


# Global executor factory
def get_tool_executor(agent_tools: List[Dict[str, Any]]) -> ToolExecutor:
    """
    Create a ToolExecutor for an agent's tools.

    Args:
        agent_tools: List of agent tool configurations

    Returns:
        ToolExecutor instance
    """
    return ToolExecutor(agent_tools)
