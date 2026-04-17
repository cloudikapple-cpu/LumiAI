"""Unit tests for LLM router."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.types import TaskType, ModelCapability
from core.interfaces import ChatMessage, ChatOptions
from app.llm.router import LLMRouter
from app.llm.providers.openrouter import OpenRouterProvider


class TestLLMRouter:
    """Tests for the LLM Router."""

    @pytest.fixture
    def router(self):
        """Create a router instance for testing."""
        return LLMRouter()

    @pytest.fixture
    def mock_provider(self):
        """Create a mock provider."""
        provider = MagicMock(spec=OpenRouterProvider)
        provider.provider_name = "test_provider"
        provider.supports_capabilities = {ModelCapability.TEXT, ModelCapability.VISION}
        provider.available_models = []
        provider.chat = AsyncMock(return_value={
            "content": "Test response",
            "model": "test-model",
            "provider": "test_provider",
            "sources": [],
            "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
        })
        provider.chat_stream = AsyncMock(return_value=iter(["chunk1", "chunk2"]))
        return provider

    def test_register_provider(self, router, mock_provider):
        """Test registering a provider."""
        router.register_provider(mock_provider, set_default=True)

        assert "test_provider" in router._providers
        assert router._default_provider == "test_provider"
        assert ModelCapability.TEXT in router._capability_map
        assert ModelCapability.VISION in router._capability_map

    def test_get_provider_for_task_text(self, router, mock_provider):
        """Test getting provider for text task."""
        router.register_provider(mock_provider, set_default=True)

        provider = router.get_provider_for_task(TaskType.CHAT)
        assert provider == mock_provider

    def test_get_provider_for_task_vision(self, router, mock_provider):
        """Test getting provider for vision task."""
        router.register_provider(mock_provider, set_default=True)

        provider = router.get_provider_for_task(TaskType.VISION_ANALYSIS)
        assert provider == mock_provider

    def test_get_provider_for_task_unknown(self, router, mock_provider):
        """Test getting provider when no provider supports the task."""
        router.register_provider(mock_provider, set_default=True)

        provider = router.get_provider_for_task(TaskType.WEB_SEARCH)
        assert provider == mock_provider

    def test_get_default_provider(self, router, mock_provider):
        """Test getting the default provider."""
        router.register_provider(mock_provider, set_default=True)

        provider = router._get_default_provider()
        assert provider == mock_provider

    def test_get_provider_by_name(self, router, mock_provider):
        """Test getting a specific provider by name."""
        router.register_provider(mock_provider)

        provider = router.get_provider("test_provider")
        assert provider == mock_provider

        provider = router.get_provider("nonexistent")
        assert provider is None

    @pytest.mark.asyncio
    async def test_chat_routes_to_provider(self, router, mock_provider):
        """Test that chat routes to the correct provider."""
        router.register_provider(mock_provider, set_default=True)

        messages = [ChatMessage(role="user", content="Hello")]
        options = ChatOptions()

        response = await router.chat(messages, options, TaskType.CHAT)

        mock_provider.chat.assert_called_once()
        assert response["content"] == "Test response"

    @pytest.mark.asyncio
    async def test_chat_with_fallback(self, router, mock_provider):
        """Test chat with fallback on error."""
        failing_provider = MagicMock()
        failing_provider.provider_name = "failing"
        failing_provider.supports_capabilities = {ModelCapability.TEXT}
        failing_provider.available_models = []
        failing_provider.chat = AsyncMock(side_effect=Exception("Provider failed"))
        failing_provider.chat_stream = AsyncMock()

        router.register_provider(failing_provider)
        router.register_provider(mock_provider, set_default=True)

        messages = [ChatMessage(role="user", content="Hello")]
        options = ChatOptions()

        response = await router.chat_with_fallback(messages, options, TaskType.CHAT)

        assert response["content"] == "Test response"
        assert failing_provider.chat.call_count == 1
        assert mock_provider.chat.call_count == 1

    def test_list_providers(self, router, mock_provider):
        """Test listing all providers."""
        router.register_provider(mock_provider)

        providers = router.list_providers()
        assert len(providers) == 1
        assert providers[0][0] == "test_provider"

    def test_get_stats(self, router, mock_provider):
        """Test getting router statistics."""
        router.register_provider(mock_provider, set_default=True)

        stats = router.get_stats()

        assert "providers" in stats
        assert "default" in stats
        assert stats["default"] == "test_provider"
        assert "test_provider" in stats["providers"]


class TestChatMessage:
    """Tests for ChatMessage dataclass."""

    def test_create_message(self):
        """Test creating a chat message."""
        msg = ChatMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.media_url is None

    def test_create_message_with_media(self):
        """Test creating a chat message with media."""
        msg = ChatMessage(role="user", content="Look at this", media_url="data:image/png;base64,abc123")
        assert msg.media_url == "data:image/png;base64,abc123"


class TestChatOptions:
    """Tests for ChatOptions dataclass."""

    def test_default_options(self):
        """Test default chat options."""
        options = ChatOptions()
        assert options.model is None
        assert options.temperature == 0.7
        assert options.max_tokens is None
        assert options.tools is None
        assert options.stream is False

    def test_custom_options(self):
        """Test custom chat options."""
        options = ChatOptions(
            model="gpt-4",
            temperature=0.5,
            max_tokens=1000,
            stream=True,
        )
        assert options.model == "gpt-4"
        assert options.temperature == 0.5
        assert options.max_tokens == 1000
        assert options.stream is True