"""Tool registry - manages all available tools."""

from typing import Any

from core.interfaces import BaseTool as InterfaceBaseTool
from core.types import TaskType

from app.tools.base import BaseTool


class ToolRegistry:
    """Registry for all tools in the system."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}
        self._task_map: dict[TaskType, list[str]] = {}

    def register(
        self,
        tool: BaseTool,
        task_types: list[TaskType] | None = None,
    ) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool

        if task_types:
            for task_type in task_types:
                if task_type not in self._task_map:
                    self._task_map[task_type] = []
if tool.name not in self._task_map[task_type]:
                self._task_map[task_type].append(tool.name)

    def get(self, name: str) -> BaseTool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def get_for_task(self, task_type: TaskType) -> list[BaseTool]:
        """Get all tools that can handle a task type."""
        tool_names = self._task_map.get(task_type, [])
        return [self._tools[name] for name in tool_names if name in self._tools]

    def list_all(self) -> list[BaseTool]:
        """List all registered tools."""
        return list(self._tools.values())

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """Get schemas for all tools (for LLM function calling)."""
        schemas = []
        for tool in self._tools.values():
            schemas.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema,
                },
            })
        return schemas

    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
        self._task_map.clear()


_global_registry: ToolRegistry | None = None


def get_registry() -> ToolRegistry:
    """Get the global tool registry instance."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
        _register_default_tools(_global_registry)
    return _global_registry


def _register_default_tools(registry: ToolRegistry) -> None:
    """Register default tools."""
    from app.tools.web_search import WebSearchTool
    from app.tools.vision import VisionTool
    from app.tools.audio import AudioTool
    from app.tools.video import VideoTool
    from app.tools.rag import RAGTool
    from app.tools.document import DocumentTool
    from core.types import TaskType

    registry.register(WebSearchTool(), [TaskType.WEB_SEARCH, TaskType.MIXED])
    registry.register(VisionTool(), [TaskType.VISION_ANALYSIS, TaskType.MIXED])
    registry.register(AudioTool(), [TaskType.AUDIO_TRANSCRIPTION])
    registry.register(VideoTool(), [TaskType.VIDEO_ANALYSIS, TaskType.MIXED])
    registry.register(RAGTool(), [TaskType.RAG])
    registry.register(DocumentTool(), [TaskType.DOCUMENT_ANALYSIS])