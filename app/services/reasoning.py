"""Reasoning pipeline - internal planning without exposing chain-of-thought."""

from typing import Any

from core.interfaces import ChatMessage, ChatOptions
from core.types import (
    MessageType,
    TaskType,
    ToolResult,
    UserMode,
)
from app.llm.router import LLMRouter, get_router
from app.tools.registry import ToolRegistry, get_registry


class ReasoningPipeline:
    """
    Internal reasoning pipeline that plans tool usage and response strategy.

    This is NOT shown to the user - it handles:
    1. Query classification (what type of request is this?)
    2. Tool planning (which tools are needed?)
    3. Data collection (execute tools, gather information)
    4. Response synthesis (form the final response)
    5. Contradiction check (verify consistency)
    6. Final output generation
    """

    def __init__(
        self,
        llm_router: LLMRouter | None = None,
        tool_registry: ToolRegistry | None = None,
    ):
        self.llm_router = llm_router or get_router()
        self.tool_registry = tool_registry or get_registry()

    async def process(
        self,
        message: str,
        message_type: MessageType,
        user_id: int,
        context: dict[str, Any],
        user_mode: UserMode = UserMode.ASSISTANT,
    ) -> dict[str, Any]:
        """
        Process a user message through the reasoning pipeline.

        Args:
            message: User message content
            message_type: Type of message (text, photo, voice, etc.)
            user_id: User ID
            context: Additional context (conversation history, etc.)
            user_mode: User's current mode (assistant, explorer, concise)

        Returns:
            Dictionary with:
            - response: The text response to send
            - reasoning: Internal reasoning (not shown to user)
            - sources: Source URLs if web search was used
            - tool_results: Results from any tools used
        """
        plan = await self._create_plan(message, message_type, user_id, context, user_mode)

        tool_results = await self._execute_tools(plan, context)

        response = await self._synthesize_response(plan, tool_results, context)

        return {
            "response": response,
            "reasoning": plan.get("reasoning"),
            "sources": self._collect_sources(tool_results),
            "tool_results": tool_results,
            "task_type": plan.get("task_type"),
        }

    async def _create_plan(
        self,
        message: str,
        message_type: MessageType,
        user_id: int,
        context: dict[str, Any],
        user_mode: UserMode,
    ) -> dict[str, Any]:
        """Create an internal plan for handling the request."""
        plan = {
            "task_type": self._classify_task(message, message_type),
            "message": message,
            "message_type": message_type,
            "user_mode": user_mode,
            "tools_needed": [],
            "web_search_needed": self._needs_web_search(message, user_mode),
            "context_needed": True,
            "reasoning": [],
        }

        plan["tools_needed"] = self._determine_tools(plan)

        return plan

    def _classify_task(self, message: str, message_type: MessageType) -> TaskType:
        """Classify the task type based on message content and type."""
        if message_type == "photo":
            return TaskType.VISION_ANALYSIS
        elif message_type == "voice":
            return TaskType.AUDIO_TRANSCRIPTION
        elif message_type == "video":
            return TaskType.VIDEO_ANALYSIS
        elif message_type == "document":
            return TaskType.DOCUMENT_ANALYSIS

        message_lower = message.lower()

        code_indicators = ["code", "function", "implement", "debug", "error", "python", "javascript"]
        if any(ind in message_lower for ind in code_indicators):
            return TaskType.CODE

        if any(word in message_lower for word in ["search", "find", "what is", "who is", "latest", "recent"]):
            return TaskType.WEB_SEARCH

        search_indicators = ["remember", "previously", "before", "my", "I told you"]
        if any(word in message_lower for word in search_indicators):
            return TaskType.RAG

        return TaskType.CHAT

    def _needs_web_search(self, message: str, user_mode: UserMode) -> bool:
        """Determine if web search is needed."""
        fresh_info_indicators = [
            "latest", "recent", "news", "current",
            "today", "yesterday", "this week",
            "2024", "2025", "2026",
        ]

        if any(ind in message.lower() for ind in fresh_info_indicators):
            return True

        if user_mode == UserMode.EXPLORER:
            return True

        return False

    def _determine_tools(self, plan: dict[str, Any]) -> list[str]:
        """Determine which tools are needed based on the plan."""
        tools = []

        if plan["web_search_needed"]:
            tools.append("web_search")

        task_type = plan["task_type"]
        if task_type == TaskType.VISION_ANALYSIS:
            tools.append("vision")
        elif task_type == TaskType.AUDIO_TRANSCRIPTION:
            tools.append("audio_transcription")
        elif task_type == TaskType.VIDEO_ANALYSIS:
            tools.append("video_analysis")
        elif task_type == TaskType.DOCUMENT_ANALYSIS:
            tools.append("document_analysis")
        elif task_type == TaskType.RAG:
            tools.append("rag")

        return tools

    async def _execute_tools(
        self,
        plan: dict[str, Any],
        context: dict[str, Any],
    ) -> list[ToolResult]:
        """Execute all needed tools and collect results."""
        results = []
        tool_context = {
            "user_id": context.get("user_id"),
            "conversation_id": context.get("conversation_id"),
        }

        for tool_name in plan["tools_needed"]:
            tool = self.tool_registry.get(tool_name)
            if not tool:
                continue

            parameters = self._build_tool_parameters(tool_name, plan, context)
            try:
                result = await tool.execute(parameters, tool_context)
                results.append(result)
            except Exception as e:
                results.append({
                    "success": False,
                    "error": str(e),
                    "sources": [],
                    "metadata": {"tool": tool_name},
                })

        return results

    def _build_tool_parameters(
        self,
        tool_name: str,
        plan: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Build parameters for a specific tool."""
        if tool_name == "web_search":
            return {
                "query": plan["message"],
                "num_results": 5 if plan["user_mode"] == UserMode.CONCISE else 10,
            }
        elif tool_name == "vision":
            return {
                "image_url": context.get("media_url", plan["message"]),
                "prompt": "Describe this image in detail" if not plan["message"] else plan["message"],
            }
        elif tool_name == "rag":
            return {
                "query": plan["message"],
                "limit": 5,
            }
        elif tool_name == "audio_transcription":
            return {
                "audio_url": context.get("media_url", plan["message"]),
            }
        elif tool_name == "video_analysis":
            return {
                "video_url": context.get("media_url"),
                "prompt": plan["message"],
            }
        elif tool_name == "document_analysis":
            return {
                "document_url": context.get("media_url"),
                "prompt": plan["message"],
            }

        return {}

    async def _synthesize_response(
        self,
        plan: dict[str, Any],
        tool_results: list[ToolResult],
        context: dict[str, Any],
    ) -> str:
        """Synthesize the final response using LLM."""
        messages = self._build_synthesis_messages(plan, tool_results, context)

        options = ChatOptions(
            temperature=0.7 if plan["user_mode"] != UserMode.CONCISE else 0.5,
            max_tokens=4096 if plan["user_mode"] != UserMode.CONCISE else 1024,
        )

        try:
            response = await self.llm_router.chat_with_fallback(
                messages=messages,
                options=options,
                task_type=plan["task_type"],
            )
            return response["content"]
        except Exception as e:
            return f"I encountered an error processing your request: {str(e)}"

    def _build_synthesis_messages(
        self,
        plan: dict[str, Any],
        tool_results: list[ToolResult],
        context: dict[str, Any],
    ) -> list[ChatMessage]:
        """Build messages for response synthesis."""
        system_prompt = self._build_system_prompt(plan)
        messages = [ChatMessage(role="system", content=system_prompt)]

        if context.get("history"):
            for msg in context["history"][-10:]:
                messages.append(ChatMessage(
                    role=msg.get("role", "user"),
                    content=msg.get("content", ""),
                ))

        tool_context = self._format_tool_results(tool_results)

        user_content = plan["message"]
        if tool_context:
            user_content += f"\n\n[Context from tools]\n{tool_context}"

        messages.append(ChatMessage(role="user", content=user_content))

        return messages

    def _build_system_prompt(self, plan: dict[str, Any]) -> str:
        """Build the system prompt based on user mode."""
        mode = plan["user_mode"]

        if mode == UserMode.CONCISE:
            return (
                "You are a concise AI assistant. Give brief, direct answers. "
                "Use minimal preamble. Get to the point quickly."
            )
        elif mode == UserMode.EXPLORER:
            return (
                "You are an in-depth research assistant. Provide comprehensive analysis. "
                "Include multiple perspectives. Cite sources when available. "
                "When information is uncertain, acknowledge it."
            )
        else:
            return (
                "You are a helpful AI assistant. Provide clear, accurate responses. "
                "Be friendly and informative. When uncertain, say so honestly."
            )

    def _format_tool_results(self, tool_results: list[ToolResult]) -> str:
        """Format tool results for inclusion in prompt."""
        if not tool_results:
            return ""

        formatted = []
        for result in tool_results:
            if result.get("success", False):
                data = result.get("data", {})
                if isinstance(data, dict):
                    if "results" in data:
                        for r in data["results"][:5]:
                            formatted.append(f"- {r.get('title', 'Result')}: {r.get('snippet', '')[:200]}")
                    elif "query" in data:
                        formatted.append(f"Search results for: {data['query']}")
                        if "results" in data:
                            for r in data["results"]:
                                formatted.append(f"  • {r.get('title', '')}: {r.get('snippet', '')[:150]}")

        return "\n".join(formatted) if formatted else ""

    def _collect_sources(self, tool_results: list[ToolResult]) -> list[str]:
        """Collect all source URLs from tool results."""
        sources = []
        for result in tool_results:
            if result.get("sources"):
                sources.extend(result["sources"])
        return sources[:10]


_pipeline: ReasoningPipeline | None = None


def get_reasoning_pipeline() -> ReasoningPipeline:
    """Get the global reasoning pipeline instance."""
    global _pipeline
    if _pipeline is None:
        _pipeline = ReasoningPipeline()
    return _pipeline