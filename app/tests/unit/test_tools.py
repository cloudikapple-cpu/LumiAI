"""Unit tests for tools."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from core.types import TaskType, ToolResult
from app.tools.base import BaseTool, execute_tool
from app.tools.registry import ToolRegistry
from app.tools.web_search import WebSearchTool
from app.tools.vision import VisionTool
from app.tools.audio import AudioTool


class TestToolExecutionError:
    """Tests for ToolExecutionError."""

    def test_error_message(self):
        """Test error message format."""
        from app.tools.base import ToolExecutionError

        error = ToolExecutionError("test_tool", "Something went wrong")
        assert error.tool_name == "test_tool"
        assert error.message == "Something went wrong"
        assert str(error).startswith("[test_tool]")

    def test_error_with_cause(self):
        """Test error with cause exception."""
        from app.tools.base import ToolExecutionError

        cause = ValueError("Invalid input")
        error = ToolExecutionError("test_tool", "Failed", cause)
        assert error.cause == cause


class TestExecuteTool:
    """Tests for execute_tool helper."""

    @pytest.mark.asyncio
    async def test_successful_execution(self):
        """Test successful tool execution."""
        tool = MagicMock(spec=BaseTool)
        tool.name = "test_tool"
        tool.execute = AsyncMock(return_value=ToolResult(
            success=True,
            data={"result": "success"},
            error=None,
            sources=[],
        ))

        result = await execute_tool(tool, {"param": "value"}, {"user_id": 123})

        tool.execute.assert_called_once_with({"param": "value"}, {"user_id": 123})
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_failed_execution(self):
        """Test failed tool execution returns error result."""
        tool = MagicMock(spec=BaseTool)
        tool.name = "test_tool"
        tool.execute = AsyncMock(side_effect=Exception("Tool failed"))

        result = await execute_tool(tool, {}, {})

        assert result["success"] is False
        assert "Tool failed" in result["error"]


class TestToolRegistry:
    """Tests for ToolRegistry."""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry for testing."""
        return ToolRegistry()

    @pytest.fixture
    def mock_tool(self):
        """Create a mock tool."""
        tool = MagicMock(spec=BaseTool)
        tool.name = "mock_tool"
        tool.description = "A mock tool"
        tool.input_schema = {"type": "object", "properties": {}}
        return tool

    def test_register_tool(self, registry, mock_tool):
        """Test registering a tool."""
        registry.register(mock_tool)
        assert registry.get("mock_tool") == mock_tool

    def test_register_tool_with_task_types(self, registry, mock_tool):
        """Test registering a tool with task types."""
        registry.register(mock_tool, [TaskType.CHAT, TaskType.CODE])
        tools = registry.get_for_task(TaskType.CHAT)
        assert mock_tool in tools

    def test_get_nonexistent_tool(self, registry):
        """Test getting a tool that doesn't exist."""
        assert registry.get("nonexistent") is None

    def test_get_tools_for_task(self, registry, mock_tool):
        """Test getting tools for a specific task."""
        registry.register(mock_tool, [TaskType.CHAT])
        tools = registry.get_for_task(TaskType.CHAT)
        assert mock_tool in tools

        tools = registry.get_for_task(TaskType.VISION_ANALYSIS)
        assert mock_tool not in tools

    def test_list_all_tools(self, registry, mock_tool):
        """Test listing all registered tools."""
        registry.register(mock_tool)
        tools = registry.list_all()
        assert mock_tool in tools

    def test_get_tool_schemas(self, registry, mock_tool):
        """Test getting tool schemas for LLM function calling."""
        registry.register(mock_tool)
        schemas = registry.get_tool_schemas()

        assert len(schemas) == 1
        assert schemas[0]["function"]["name"] == "mock_tool"
        assert schemas[0]["function"]["description"] == "A mock tool"

    def test_clear_registry(self, registry, mock_tool):
        """Test clearing all tools from registry."""
        registry.register(mock_tool)
        registry.clear()
        assert len(registry.list_all()) == 0


class TestWebSearchTool:
    """Tests for WebSearchTool."""

    @pytest.fixture
    def tool(self):
        """Create a WebSearchTool instance."""
        return WebSearchTool()

    def test_tool_properties(self, tool):
        """Test tool has correct properties."""
        assert tool.name == "web_search"
        assert "search" in tool.description.lower()
        assert "query" in tool.input_schema["required"]

    def test_input_schema(self, tool):
        """Test input schema structure."""
        schema = tool.input_schema
        assert schema["type"] == "object"
        assert "query" in schema["properties"]
        assert "num_results" in schema["properties"]
        assert "num_results" in schema.get("properties", {}).get("num_results", {}).get("default", None) or schema["properties"]["num_results"].get("default") == 5

    @pytest.mark.asyncio
    async def test_execute_missing_query(self, tool):
        """Test execution fails without query parameter."""
        result = await tool.execute({}, {"user_id": 123})

        assert result["success"] is False
        assert "query" in result["error"].lower()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_execute_with_query(self, mock_client, tool):
        """Test execution with query parameter."""
        mock_response = MagicMock()
        mock_response.text = """
        <a class="result__a" href="https://example.com">Example</a>
        <a class="result__snippet">This is a test snippet</a>
        """
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_client_instance
        mock_client_instance.aclose = AsyncMock()

        result = await tool.execute({"query": "test query"}, {"user_id": 123})

        assert result["success"] is True
        assert "query" in result["data"]


class TestVisionTool:
    """Tests for VisionTool."""

    @pytest.fixture
    def tool(self):
        """Create a VisionTool instance."""
        return VisionTool()

    def test_tool_properties(self, tool):
        """Test tool has correct properties."""
        assert tool.name == "vision"
        assert "image" in tool.description.lower() or "analyze" in tool.description.lower()

    def test_input_schema(self, tool):
        """Test input schema requires image_url and prompt."""
        schema = tool.input_schema
        assert "image_url" in schema["required"]
        assert "prompt" in schema["required"]

    @pytest.mark.asyncio
    async def test_execute_missing_image_url(self, tool):
        """Test execution fails without image_url."""
        result = await tool.execute({"prompt": "Describe"}, {"user_id": 123})

        assert result["success"] is False
        assert "image_url" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_missing_prompt(self, tool):
        """Test execution fails without prompt."""
        result = await tool.execute({"image_url": "http://example.com/image.jpg"}, {"user_id": 123})

        assert result["success"] is False
        assert "prompt" in result["error"].lower()


class TestAudioTool:
    """Tests for AudioTool."""

    @pytest.fixture
    def tool(self):
        """Create an AudioTool instance."""
        return AudioTool()

    def test_tool_properties(self, tool):
        """Test tool has correct properties."""
        assert tool.name == "audio_transcription"
        assert "audio" in tool.description.lower() or "voice" in tool.description.lower()

    def test_input_schema(self, tool):
        """Test input schema requires audio_url."""
        schema = tool.input_schema
        assert "audio_url" in schema["required"]

    @pytest.mark.asyncio
    async def test_execute_missing_audio_url(self, tool):
        """Test execution fails without audio_url."""
        result = await tool.execute({}, {"user_id": 123})

        assert result["success"] is False
        assert "audio_url" in result["error"].lower()