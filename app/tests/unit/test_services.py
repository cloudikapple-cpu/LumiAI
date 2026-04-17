"""Unit tests for services."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from core.types import TaskType, UserMode, MessageType
from app.services.reasoning import ReasoningPipeline


class TestReasoningPipeline:
    """Tests for ReasoningPipeline."""

    @pytest.fixture
    def mock_router(self):
        """Create a mock LLM router."""
        router = MagicMock()
        router.chat_with_fallback = AsyncMock(return_value={
            "content": "Test response from LLM",
            "model": "test-model",
            "provider": "test",
            "sources": [],
            "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
        })
        return router

    @pytest.fixture
    def mock_registry(self):
        """Create a mock tool registry."""
        registry = MagicMock()
        return registry

    @pytest.fixture
    def pipeline(self, mock_router, mock_registry):
        """Create a ReasoningPipeline with mocked dependencies."""
        return ReasoningPipeline(
            llm_router=mock_router,
            tool_registry=mock_registry,
        )

    def test_classify_task_text(self, pipeline):
        """Test task classification for text messages."""
        task = pipeline._classify_task("Hello, how are you?", MessageType.TEXT)
        assert task == TaskType.CHAT

    def test_classify_task_code(self, pipeline):
        """Test task classification for code requests."""
        task = pipeline._classify_task("Write Python code for me", MessageType.TEXT)
        assert task == TaskType.CODE

    def test_classify_task_search(self, pipeline):
        """Test task classification for search queries."""
        task = pipeline._classify_task("What is the latest news?", MessageType.TEXT)
        assert task == TaskType.WEB_SEARCH

    def test_classify_task_rag(self, pipeline):
        """Test task classification for memory recall."""
        task = pipeline._classify_task("Remember what I told you about my cat?", MessageType.TEXT)
        assert task == TaskType.RAG

    def test_classify_task_photo(self, pipeline):
        """Test task classification for photos."""
        task = pipeline._classify_task("", MessageType.PHOTO)
        assert task == TaskType.VISION_ANALYSIS

    def test_classify_task_voice(self, pipeline):
        """Test task classification for voice."""
        task = pipeline._classify_task("", MessageType.VOICE)
        assert task == TaskType.AUDIO_TRANSCRIPTION

    def test_classify_task_video(self, pipeline):
        """Test task classification for video."""
        task = pipeline._classify_task("", MessageType.VIDEO)
        assert task == TaskType.VIDEO_ANALYSIS

    def test_classify_task_document(self, pipeline):
        """Test task classification for document."""
        task = pipeline._classify_task("", MessageType.DOCUMENT)
        assert task == TaskType.DOCUMENT_ANALYSIS

    def test_needs_web_search_fresh_info(self, pipeline):
        """Test web search needed for fresh information requests."""
        assert pipeline._needs_web_search("What's the latest news?", UserMode.ASSISTANT) is True
        assert pipeline._needs_web_search("News today", UserMode.ASSISTANT) is True
        assert pipeline._needs_web_search("2026 events", UserMode.ASSISTANT) is True

    def test_needs_web_search_explorer_mode(self, pipeline):
        """Test web search always enabled in explorer mode."""
        assert pipeline._needs_web_search("Hello", UserMode.EXPLORER) is True

    def test_needs_web_search_concise_mode(self, pipeline):
        """Test web search based on query in concise mode."""
        assert pipeline._needs_web_search("Hello", UserMode.CONCISE) is False
        assert pipeline._needs_web_search("latest news", UserMode.CONCISE) is True

    def test_determine_tools_no_search(self, pipeline):
        """Test tool determination for simple chat."""
        plan = {
            "task_type": TaskType.CHAT,
            "web_search_needed": False,
        }
        tools = pipeline._determine_tools(plan)
        assert "web_search" not in tools

    def test_determine_tools_with_search(self, pipeline):
        """Test tool determination with web search."""
        plan = {
            "task_type": TaskType.CHAT,
            "web_search_needed": True,
        }
        tools = pipeline._determine_tools(plan)
        assert "web_search" in tools

    def test_determine_tools_vision(self, pipeline):
        """Test tool determination for vision tasks."""
        plan = {
            "task_type": TaskType.VISION_ANALYSIS,
            "web_search_needed": False,
        }
        tools = pipeline._determine_tools(plan)
        assert "vision" in tools

    def test_determine_tools_rag(self, pipeline):
        """Test tool determination for RAG tasks."""
        plan = {
            "task_type": TaskType.RAG,
            "web_search_needed": False,
        }
        tools = pipeline._determine_tools(plan)
        assert "rag" in tools

    @pytest.mark.asyncio
    async def test_process_simple_chat(self, pipeline, mock_router, mock_registry):
        """Test processing a simple chat message."""
        mock_registry.get = MagicMock(return_value=None)

        result = await pipeline.process(
            message="Hello!",
            message_type=MessageType.TEXT,
            user_id=123,
            context={},
            user_mode=UserMode.ASSISTANT,
        )

        assert "response" in result
        assert result["response"] == "Test response from LLM"
        mock_router.chat_with_fallback.assert_called_once()

    def test_build_system_prompt_concise(self, pipeline):
        """Test system prompt for concise mode."""
        plan = {"user_mode": UserMode.CONCISE}
        prompt = pipeline._build_system_prompt(plan)
        assert "concise" in prompt.lower()
        assert "brief" in prompt.lower()

    def test_build_system_prompt_explorer(self, pipeline):
        """Test system prompt for explorer mode."""
        plan = {"user_mode": UserMode.EXPLORER}
        prompt = pipeline._build_system_prompt(plan)
        assert "research" in prompt.lower() or "comprehensive" in prompt.lower()

    def test_build_system_prompt_assistant(self, pipeline):
        """Test system prompt for assistant mode."""
        plan = {"user_mode": UserMode.ASSISTANT}
        prompt = pipeline._build_system_prompt(plan)
        assert "helpful" in prompt.lower()

    def test_collect_sources_empty(self, pipeline):
        """Test collecting sources from empty results."""
        sources = pipeline._collect_sources([])
        assert sources == []

    def test_collect_sources_with_results(self, pipeline):
        """Test collecting sources from tool results."""
        tool_results = [
            {"sources": ["https://example1.com"]},
            {"sources": ["https://example2.com", "https://example3.com"]},
        ]
        sources = pipeline._collect_sources(tool_results)
        assert len(sources) == 3
        assert "https://example1.com" in sources


class TestMessageTypes:
    """Tests for message type classifications."""

    def test_message_type_values(self):
        """Test that all expected message types exist."""
        from core.types import MessageType
        assert MessageType.TEXT == "text"
        assert MessageType.PHOTO == "photo"
        assert MessageType.VOICE == "voice"
        assert MessageType.VIDEO == "video"
        assert MessageType.DOCUMENT == "document"


class TestUserMode:
    """Tests for user mode enumerations."""

    def test_user_mode_values(self):
        """Test that all expected user modes exist."""
        from core.types import UserMode
        assert UserMode.ASSISTANT.value == "assistant"
        assert UserMode.EXPLORER.value == "explorer"
        assert UserMode.CONCISE.value == "concise"