"""Base classes for tools."""

from abc import ABC, abstractmethod
from typing import Any

from core.interfaces import BaseTool as InterfaceBaseTool
from core.types import ToolResult, TaskType


class BaseTool(InterfaceBaseTool, ABC):
    """Base class for all tools in the system."""

    def matches_task(self, task_type: TaskType) -> bool:
        """Check if this tool can handle the given task type."""
        return False


class ToolExecutionError(Exception):
    """Raised when tool execution fails."""

    def __init__(self, tool_name: str, message: str, cause: Exception | None = None):
        self.tool_name = tool_name
        self.message = message
        self.cause = cause
        super().__init__(f"[{tool_name}] {message}")


async def execute_tool(
    tool: BaseTool,
    parameters: dict[str, Any],
    context: dict[str, Any],
) -> ToolResult:
    """
    Execute a tool with error handling.

    Args:
        tool: The tool to execute
        parameters: Tool parameters
        context: Execution context

    Returns:
        ToolResult with success/error information
    """
    try:
        result = await tool.execute(parameters, context)
        return result
    except Exception as e:
        return ToolResult(
            success=False,
            data=None,
            error=str(e),
            sources=[],
            metadata={},
        )