"""
Generic OpenAI-Compatible Provider Base Class

This module provides a base implementation for LLM providers that are compatible
with the OpenAI API format. It handles common functionality like HTTP sessions,
API calls, and streaming responses.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional, Union

import aiohttp

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(ABC):
    """
    Abstract base class for OpenAI-compatible LLM providers

    This class provides common functionality for providers that use the
    OpenAI API format, including:
    - HTTP session management
    - API request formatting
    - Response parsing
    - Streaming support
    - Property mapping
    - Tool/function calling support
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the provider with configuration

        Args:
            config: Provider-specific configuration dictionary
        """
        self.config = config
        self._session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session"""
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    @abstractmethod
    def _get_api_url(self) -> str:
        """
        Get the full API URL for completions

        Returns:
            str: Complete API URL
        """
        pass

    @abstractmethod
    def _get_headers(self) -> Dict[str, str]:
        """
        Get HTTP headers for API requests

        Returns:
            Dict[str, str]: HTTP headers
        """
        pass

    def _validate_config(self):
        """Validate that required configuration is present"""
        if not self.config.get("api_key"):
            raise ValueError(f"{self.__class__.__name__}: API key is required")

        # API URL is now provided by constants, not configuration
        # The _get_api_url() method should handle URL construction using constants

    def _prepare_request_data(
        self,
        prompt: str,
        model: str = None,
        stream: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Prepare the request data for the API call

        Args:
            prompt: Input text prompt (used if messages not provided)
            model: Model to use for generation
            stream: Whether to stream the response
            tools: Optional list of tool definitions for function calling
            messages: Optional list of messages (overrides prompt if provided)
            **kwargs: Additional parameters for the API call

        Returns:
            Dict[str, Any]: Request data
        """
        # Use provided messages or create from prompt
        if messages:
            request_messages = messages
        else:
            request_messages = [
                {
                    "role": "user",
                    "content": prompt,
                }
            ]

        data = {
            "model": model or self.config.get("model", "default-model"),
            "messages": request_messages,
            "stream": stream,
            **kwargs,
        }

        # Add tools if provided
        if tools:
            data["tools"] = tools
            # Allow model to choose whether to call a tool
            data["tool_choice"] = "auto"

        return data

    async def generate(
        self,
        prompt: str,
        model: str = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> Union[str, Dict[str, Any]]:
        """
        Generate text using the provider's API

        Args:
            prompt: Input text prompt
            model: Model to use for generation (overrides config)
            tools: Optional list of tool definitions for function calling
            messages: Optional list of messages for multi-turn conversation
            **kwargs: Additional parameters for the API call

        Returns:
            str: Generated text (if no tool calls)
            Dict: Full response with tool_calls (if model wants to call tools)

        Raises:
            ValueError: If required configuration is missing
            RuntimeError: If API call fails
        """
        self._validate_config()

        session = await self._get_session()
        headers = self._get_headers()
        data = self._prepare_request_data(prompt, model, stream=False, tools=tools, messages=messages, **kwargs)
        api_url = self._get_api_url()

        try:
            async with session.post(api_url, headers=headers, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"{self.__class__.__name__} API error {response.status}: {error_text}")

                result = await response.json()
                message = result["choices"][0]["message"]

                # Check if model wants to call tools
                if message.get("tool_calls"):
                    return {
                        "type": "tool_calls",
                        "tool_calls": message["tool_calls"],
                        "content": message.get("content"),
                    }

                return message.get("content", "")

        except Exception as e:
            raise RuntimeError(f"{self.__class__.__name__} API error: {str(e)}")

    async def generate_stream(
        self,
        prompt: str,
        model: str = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> AsyncIterator[Union[str, Dict[str, Any]]]:
        """
        Stream text generation using the provider's API

        Args:
            prompt: Input text prompt
            model: Model to use for generation (overrides config)
            tools: Optional list of tool definitions for function calling
            messages: Optional list of messages for multi-turn conversation
            **kwargs: Additional parameters for the API call

        Yields:
            str: Generated text chunks
            Dict: Tool call chunks (if model wants to call tools)

        Raises:
            ValueError: If required configuration is missing
            RuntimeError: If API call fails
        """
        self._validate_config()

        session = await self._get_session()
        headers = self._get_headers()
        data = self._prepare_request_data(prompt, model, stream=True, tools=tools, messages=messages, **kwargs)
        api_url = self._get_api_url()

        try:
            async with session.post(api_url, headers=headers, json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"{self.__class__.__name__} API error {response.status}: {error_text}")

                # Track tool calls across chunks (they come in pieces)
                tool_calls_buffer: Dict[int, Dict[str, Any]] = {}

                async for line in response.content:
                    if line:
                        line = line.decode("utf-8").strip()
                        if line.startswith("data: "):
                            data_line = line[6:]  # Remove 'data: ' prefix
                            if data_line == "[DONE]":
                                # If we have accumulated tool calls, yield them
                                if tool_calls_buffer:
                                    yield {
                                        "type": "tool_calls",
                                        "tool_calls": list(tool_calls_buffer.values()),
                                    }
                                break
                            try:
                                chunk_data = json.loads(data_line)
                                if "choices" in chunk_data and len(chunk_data["choices"]) > 0:
                                    delta = chunk_data["choices"][0].get("delta", {})

                                    # Handle text content
                                    if "content" in delta and delta["content"] is not None:
                                        yield delta["content"]

                                    # Handle tool calls (accumulated across chunks)
                                    if "tool_calls" in delta:
                                        for tc in delta["tool_calls"]:
                                            idx = tc.get("index", 0)
                                            if idx not in tool_calls_buffer:
                                                tool_calls_buffer[idx] = {
                                                    "id": tc.get("id", ""),
                                                    "type": "function",
                                                    "function": {
                                                        "name": "",
                                                        "arguments": "",
                                                    },
                                                }

                                            # Update with new data
                                            if tc.get("id"):
                                                tool_calls_buffer[idx]["id"] = tc["id"]
                                            if tc.get("function", {}).get("name"):
                                                tool_calls_buffer[idx]["function"]["name"] = tc["function"]["name"]
                                            if tc.get("function", {}).get("arguments"):
                                                tool_calls_buffer[idx]["function"]["arguments"] += tc["function"]["arguments"]

                            except json.JSONDecodeError:
                                continue

        except Exception as e:
            raise RuntimeError(f"{self.__class__.__name__} API streaming error: {str(e)}")

    async def close(self):
        """Close the HTTP session"""
        if self._session:
            await self._session.close()
            self._session = None

    @classmethod
    def get_expected_properties(cls) -> list:
        """
        Get the list of expected properties for this provider.

        Returns:
            List of property names that this provider expects
        """
        return ["model", "api_key"]

    @classmethod
    def get_field_definitions(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get the field definitions for this provider.

        Returns:
            Dictionary mapping field names to field metadata
        """
        return {
            "model": {"type": "text", "label": "Model", "required": True, "description": "Model name for generation"},
            "api_key": {
                "type": "password",
                "label": "API Key",
                "required": True,
                "description": "API key for authentication",
            },
        }
