"""LLM Router - routes requests to appropriate provider based on task type."""

from typing import Any

from app.llm.providers.base import BaseLLMProvider
from app.llm.providers.openrouter import OpenRouterProvider
from app.llm.providers.nvidia_nim import NvidiaNimProvider
from app.llm.providers.groq import GroqProvider
from core.interfaces import ChatMessage, ChatOptions, ModelInfo, LLMProvider
from core.types import LLMResponse, ModelCapability, TaskType


class LLMRouter:
    """
    Routes LLM requests to the appropriate provider based on:
    - Task type (vision, text, audio, etc.)
    - Model capabilities
    - Cost and latency preferences
    - Provider availability
    """

    def __init__(self):
        self._providers: dict[str, BaseLLMProvider] = {}
        self._default_provider: str | None = None
        self._capability_map: dict[ModelCapability, list[str]] = {}

    def register_provider(self, provider: BaseLLMProvider, set_default: bool = False) -> None:
        """Register a provider."""
        self._providers[provider.provider_name] = provider

        for capability in provider.supports_capabilities:
            if capability not in self._capability_map:
                self._capability_map[capability] = []
            self._capability_map[capability].append(provider.provider_name)

        if set_default or not self._default_provider:
            self._default_provider = provider.provider_name

    def get_provider_for_task(self, task_type: TaskType) -> BaseLLMProvider:
        """Get the best provider for a given task type."""
        if task_type == TaskType.VISION_ANALYSIS:
            required = {ModelCapability.VISION}
        elif task_type == TaskType.AUDIO_TRANSCRIPTION:
            required = {ModelCapability.AUDIO}
        elif task_type == TaskType.VIDEO_ANALYSIS:
            required = {ModelCapability.VISION, ModelCapability.AUDIO}
        elif task_type == TaskType.WEB_SEARCH:
            required = {ModelCapability.TEXT, ModelCapability.TOOL_CALLING}
        elif task_type == TaskType.CODE:
            required = {ModelCapability.TEXT}
        else:
            required = {ModelCapability.TEXT}

        for capability in required:
            provider_names = self._capability_map.get(capability, [])
            for name in provider_names:
                provider = self._providers.get(name)
                if provider:
                    return provider

        return self._get_default_provider()

    def _get_default_provider(self) -> BaseLLMProvider:
        """Get the default provider."""
        if not self._default_provider:
            raise RuntimeError("No LLM providers registered")
        provider = self._providers.get(self._default_provider)
        if not provider:
            raise RuntimeError(f"Default provider {self._default_provider} not found")
        return provider

    def get_provider(self, name: str) -> BaseLLMProvider | None:
        """Get a specific provider by name."""
        return self._providers.get(name)

    async def chat(
        self,
        messages: list[ChatMessage],
        options: ChatOptions,
        task_type: TaskType = TaskType.CHAT,
    ) -> LLMResponse:
        """Route a chat request to the appropriate provider."""
        provider = self.get_provider_for_task(task_type)
        return await provider.chat(messages, options)

    async def chat_with_fallback(
        self,
        messages: list[ChatMessage],
        options: ChatOptions,
        task_type: TaskType = TaskType.CHAT,
        preferred_provider: str | None = None,
    ) -> LLMResponse:
        """Route with fallback on failure."""
        errors = []

        if preferred_provider:
            provider = self._providers.get(preferred_provider)
            if provider:
                try:
                    return await provider.chat(messages, options)
                except Exception as e:
                    errors.append(f"{provider.provider_name}: {str(e)}")

        provider = self.get_provider_for_task(task_type)
        if preferred_provider and provider.provider_name == preferred_provider:
            pass

        try:
            return await provider.chat(messages, options)
        except Exception as e:
            errors.append(f"{provider.provider_name}: {str(e)}")

        for name, alt_provider in self._providers.items():
            if name == provider.provider_name:
                continue
            try:
                return await alt_provider.chat(messages, options)
            except Exception as e:
                errors.append(f"{name}: {str(e)}")

        raise RuntimeError(f"All providers failed: {errors}")

    def list_providers(self) -> list[tuple[str, list[ModelInfo]]]:
        """List all registered providers and their models."""
        return [
            (name, provider.available_models)
            for name, provider in self._providers.items()
        ]

    def get_stats(self) -> dict[str, Any]:
        """Get router statistics."""
        return {
            "providers": {
                name: {
                    "models": len(p.available_models),
                    "capabilities": list(p.supports_capabilities),
                    "healthy": p.healthcheck() if hasattr(p, "healthcheck") else None,
                }
                for name, p in self._providers.items()
            },
            "default": self._default_provider,
        }


def create_router() -> LLMRouter:
    """Create and configure the LLM router."""
    from app.config import settings

    router = LLMRouter()

    router.register_provider(
        OpenRouterProvider(
            api_key=settings.llm.openrouter_api_key,
            base_url=settings.llm.openrouter_base_url,
        ),
        set_default=True,
    )

    if settings.llm.nvidia_api_key:
        router.register_provider(
            NvidiaNimProvider(
                api_key=settings.llm.nvidia_api_key,
                base_url=settings.llm.nvidia_base_url,
            ),
        )

    if settings.llm.groq_api_key:
        router.register_provider(
            GroqProvider(
                api_key=settings.llm.groq_api_key,
                base_url=settings.llm.groq_base_url,
            ),
        )

    return router


_global_router: LLMRouter | None = None


def get_router() -> LLMRouter:
    """Get the global LLM router instance."""
    global _global_router
    if _global_router is None:
        _global_router = create_router()
    return _global_router