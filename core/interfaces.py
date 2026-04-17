"""Core interfaces/abstractions for LLM providers and tools."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from core.types import (
    LLMResponse,
    ModelCapability,
    TaskType,
    ToolResult,
)


@dataclass
class ModelInfo:
    """Information about a model."""

    model_id: str
    provider: str
    capabilities: set[ModelCapability] = field(default_factory=set)
    max_tokens: int = 4096
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    avg_latency_ms: float = 0.0
    context_window: int = 128_000


@dataclass
class ChatMessage:
    """A single chat message."""

    role: str  # "user", "assistant", "system"
    content: str
    media_url: str | None = None


@dataclass
class ChatOptions:
    """Options for chat completion."""

    model: str | None = None
    temperature: float = 0.7
    max_tokens: int | None = None
    tools: list[dict[str, Any]] | None = None
    tool_choice: str | None = None
    reasoning: bool = False
    stream: bool = False


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider name (e.g., 'openrouter', 'groq')."""
        pass

    @property
    @abstractmethod
    def available_models(self) -> list[ModelInfo]:
        """List of available models from this provider."""
        pass

    @property
    @abstractmethod
    def supports_capabilities(self) -> set[ModelCapability]:
        """Set of capabilities this provider supports."""
        pass

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        options: ChatOptions,
    ) -> LLMResponse:
        """
        Send a chat completion request.

        Args:
            messages: List of chat messages
            options: Chat options

        Returns:
            LLMResponse with content and metadata
        """
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[ChatMessage],
        options: ChatOptions,
    ) -> AsyncIterator[str]:
        """
        Send a streaming chat completion request.

        Args:
            messages: List of chat messages
            options: Chat options with stream=True

        Yields:
            Text chunks as they arrive
        """
        pass

    @abstractmethod
    async def healthcheck(self) -> bool:
        """Check if the provider is available."""
        pass


class BaseTool(ABC):
    """Abstract base class for tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for the LLM."""
        pass

    @property
    @abstractmethod
    def input_schema(self) -> dict[str, Any]:
        """JSON Schema for tool input."""
        pass

    @abstractmethod
    async def execute(self, parameters: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        """
        Execute the tool.

        Args:
            parameters: Tool parameters from LLM
            context: Execution context (user_id, conversation_id, etc.)

        Returns:
            ToolResult with success status and data
        """
        pass

    def matches_task(self, task_type: TaskType) -> bool:
        """Check if this tool can handle the given task type."""
        return False


class ToolRouter:
    """Routes tasks to appropriate tools."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._task_to_tool: dict[TaskType, list[str]] = {}

    def register(self, tool: BaseTool, task_types: list[TaskType] | None = None) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool
        if task_types:
            for task_type in task_types:
                if task_type not in self._task_to_tool:
                    self._task_to_tool[task_type] = []
                self._task_to_tool[task_type].append(tool.name)

    def get_tool(self, name: str) -> BaseTool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def get_tools_for_task(self, task_type: TaskType) -> list[BaseTool]:
        """Get all tools that can handle a task type."""
        tool_names = self._task_to_tool.get(task_type, [])
        return [self._tools[name] for name in tool_names if name in self._tools]

    def list_tools(self) -> list[BaseTool]:
        """List all registered tools."""
        return list(self._tools.values())