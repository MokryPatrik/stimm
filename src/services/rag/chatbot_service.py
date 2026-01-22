"""
Chatbot Service for RAG Integration

This module provides a service layer for the chatbot functionality
that avoids circular dependencies with the RAG routes.
"""

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from ..agents_admin.agent_service import AgentService
from ..llm.llm import LLMService
from ..tools import ToolExecutor, get_tool_executor
from .config import rag_config
from .rag_service import _touch_conversation
from .rag_state import RagState

LOGGER = logging.getLogger("rag_chatbot")

# Maximum number of tool call rounds to prevent infinite loops
MAX_TOOL_ROUNDS = 5


class ChatbotService:
    """Service for handling chatbot operations with RAG integration"""

    def __init__(self):
        # LLM service will be created per request with agent configuration
        self.llm_service = None
        self._is_prewarmed = False
        self._tool_executor: Optional[ToolExecutor] = None

    async def prewarm_models(self, agent_id: str = None, session_id: str = None):
        """Pre-warm models and connections at startup"""
        if self._is_prewarmed:
            return

        LOGGER.info("Pre-warming chatbot models and connections...")
        start_time = time.time()

        try:
            # Create LLM service with agent configuration for pre-warming
            llm_service = LLMService(agent_id=agent_id, session_id=session_id)

            # Pre-warm with a simple query to load models
            dummy_query = "hello"
            try:
                # This will trigger model loading if not already loaded
                async for _ in llm_service.generate_stream(dummy_query):
                    break
            except Exception as e:
                LOGGER.debug(f"Pre-warm query completed (expected): {e}")

            self._is_prewarmed = True
            prewarm_time = time.time() - start_time
            LOGGER.info(f"Chatbot models pre-warmed in {prewarm_time:.2f}s")

        except Exception as e:
            LOGGER.error(f"Failed to pre-warm chatbot models: {e}")
        finally:
            if "llm_service" in locals() and llm_service:
                await llm_service.close()

    async def process_chat_message(
        self,
        message: str,
        conversation_id: str = None,
        rag_state: RagState = None,
        agent_id: str = None,
        session_id: str = None,
        call_context: Dict[str, Any] = None,
    ):
        """
        Process a chat message and return a streaming response.
        
        Flow:
        1. Get conversation history
        2. Retrieve RAG context based on the full conversation
        3. Send system prompt + RAG context + full conversation to LLM
        4. Handle tool calls if needed
        5. Stream response back

        Args:
            message: User message
            conversation_id: Optional conversation ID
            rag_state: RAG state instance
            agent_id: Optional agent ID for provider configuration
            session_id: Optional session ID for tracking
            call_context: Optional call context for voice calls

        Yields:
            Dict with response data
        """
        conversation_id = conversation_id or str(uuid.uuid4())
        processing_start = time.time()
        rag_time = 0
        contexts = []

        try:
            # Create LLM service with agent configuration
            self.llm_service = LLMService(agent_id=agent_id, session_id=session_id)

            # Ensure models are pre-warmed
            if not self._is_prewarmed:
                await self.prewarm_models(agent_id=agent_id, session_id=session_id)

            # Load agent's enabled tools
            tools_for_llm = []
            if agent_id:
                try:
                    agent_service = AgentService()
                    agent_tools = agent_service.get_agent_tools_enabled(uuid.UUID(agent_id))
                    if agent_tools:
                        self._tool_executor = get_tool_executor(agent_tools)
                        tools_for_llm = self._tool_executor.get_tools_for_llm()
                        LOGGER.info(f"Loaded {len(tools_for_llm)} tools for agent {agent_id}")
                except Exception as e:
                    LOGGER.warning(f"Failed to load agent tools: {e}")

            # Add user message to conversation history
            async with rag_state.lock:
                await rag_state.ensure_ready()
                user_message = {
                    "role": "user",
                    "content": message,
                    "metadata": {},
                    "created_at": time.time(),
                }
                await _touch_conversation(rag_state, conversation_id, user_message)

            # Get conversation history for RAG query building
            conversation_messages = []
            if conversation_id in rag_state.conversations:
                conv_entry = rag_state.conversations[conversation_id]
                conversation_messages = conv_entry.messages.copy()

            # Build RAG search query from recent conversation context
            # Use last few messages to understand what user is looking for
            rag_query = self._build_rag_query(conversation_messages)
            LOGGER.info(f"RAG query: {rag_query[:150]}...")

            # Retrieve RAG context if available
            context_text = ""
            if not rag_state.skip_retrieval and rag_state.retrieval_engine is not None:
                rag_start = time.time()
                async with rag_state.lock:
                    contexts = await rag_state.retrieval_engine.retrieve_contexts(
                        text=rag_query,
                        namespace=None,
                        use_cache=True,
                    )
                rag_time = time.time() - rag_start
                LOGGER.info(f"RAG retrieval: {len(contexts)} contexts in {rag_time:.3f}s")
                context_text = "\n\n".join([ctx.text for ctx in contexts])

            # Build system prompt
            if self.llm_service.agent_config and self.llm_service.agent_config.system_prompt:
                system_prompt = self.llm_service.agent_config.system_prompt
            else:
                system_prompt = rag_config.get_system_prompt()

            # Add RAG context to system prompt if available
            if context_text:
                system_prompt = f"{system_prompt}\n\n## Product Catalog (use this to answer product questions):\nThe following products match the customer's query. Use this information to recommend products, compare options, and answer questions about prices and specifications. Do NOT call the product_stock tool unless customer specifically asks about stock availability.\n\n{context_text}"

            # Add call context if available (for voice calls)
            if call_context and call_context.get("caller_phone"):
                system_prompt += f"\n\n## Call Context\nCaller phone: {call_context['caller_phone']}"

            # Build messages array for LLM (OpenAI chat format)
            messages: List[Dict[str, Any]] = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Add conversation history (last N messages)
            for msg in conversation_messages[-10:]:  # Last 10 messages
                role = msg.get("role")
                content = msg.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})

            LOGGER.info(f"Sending {len(messages)} messages to LLM (1 system + {len(messages)-1} conversation)")

            # Stream the LLM response with tool calling support
            full_response = ""
            first_token_sent = False
            llm_start = time.time()
            tool_round = 0

            while tool_round < MAX_TOOL_ROUNDS:
                tool_round += 1
                accumulated_tool_calls = []
                response_text = ""

                async for chunk in self.llm_service.generate_stream(
                    prompt="",  # Not used when messages are provided
                    messages=messages,
                    tools=tools_for_llm if tools_for_llm else None,
                ):
                    # Check if this is a tool call response
                    if isinstance(chunk, dict) and chunk.get("type") == "tool_calls":
                        accumulated_tool_calls = chunk.get("tool_calls", [])
                        LOGGER.info(f"LLM requested tool calls: {[tc.get('function', {}).get('name') for tc in accumulated_tool_calls]}")
                        break
                    
                    # Regular text chunk
                    if isinstance(chunk, str):
                        response_text += chunk
                        full_response += chunk

                        # Track first token
                        if not first_token_sent:
                            first_token_sent = True
                            first_token_time = time.time() - processing_start
                            yield {
                                "type": "first_token",
                                "content": chunk,
                                "conversation_id": conversation_id,
                                "latency_metrics": {
                                    "rag_retrieval_time": rag_time,
                                    "first_token_time": first_token_time,
                                    "total_processing_time": first_token_time,
                                },
                            }
                        else:
                            yield {"type": "chunk", "content": chunk, "conversation_id": conversation_id}

                # If no tool calls, we're done
                if not accumulated_tool_calls:
                    break

                # Execute tool calls
                if self._tool_executor and accumulated_tool_calls:
                    LOGGER.info(f"Executing {len(accumulated_tool_calls)} tool calls")
                    
                    yield {
                        "type": "tool_execution",
                        "conversation_id": conversation_id,
                        "tools": [tc.get("function", {}).get("name") for tc in accumulated_tool_calls],
                    }

                    tool_results = await self._tool_executor.execute_tool_calls(accumulated_tool_calls)

                    # Add assistant message with tool calls
                    messages.append({
                        "role": "assistant",
                        "content": response_text if response_text else None,
                        "tool_calls": accumulated_tool_calls,
                    })

                    # Add tool results
                    for result in tool_results:
                        messages.append(result)

            llm_time = time.time() - llm_start
            total_time = time.time() - processing_start

            # Save assistant response to conversation
            async with rag_state.lock:
                assistant_message = {
                    "role": "assistant",
                    "content": full_response,
                    "metadata": {},
                    "created_at": time.time(),
                }
                await _touch_conversation(rag_state, conversation_id, assistant_message)

            yield {
                "type": "complete",
                "conversation_id": conversation_id,
                "latency_metrics": {
                    "rag_retrieval_time": rag_time,
                    "llm_generation_time": llm_time,
                    "total_processing_time": total_time,
                },
            }

            LOGGER.info(f"Total: {total_time:.3f}s (RAG: {rag_time:.3f}s, LLM: {llm_time:.3f}s)")

        except Exception as e:
            LOGGER.error(f"Error in chat processing: {e}", exc_info=True)
            yield {"type": "error", "content": str(e)}
        finally:
            if self.llm_service:
                await self.llm_service.close()
            if self._tool_executor:
                await self._tool_executor.close()
                self._tool_executor = None

    def _build_rag_query(self, conversation_messages: List[Dict[str, Any]]) -> str:
        """
        Build a RAG search query from conversation history.
        
        Takes recent user messages and combines them to understand
        what products/topics the user is interested in.
        """
        if not conversation_messages:
            return ""
        
        # Get last few user messages to build context
        user_messages = [
            msg.get("content", "") 
            for msg in conversation_messages[-6:]  # Last 6 messages
            if msg.get("role") == "user" and msg.get("content")
        ]
        
        if not user_messages:
            return ""
        
        # Combine recent user messages for better RAG retrieval
        # The most recent message is most important
        if len(user_messages) == 1:
            return user_messages[0]
        
        # Combine last 2-3 user messages
        return " ".join(user_messages[-3:])


# Global chatbot service instance
chatbot_service = ChatbotService()
