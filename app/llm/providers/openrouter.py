"""OpenRouter provider implementation."""

import base64
from typing import Any, AsyncIterator

import httpx

from core.interfaces import ChatMessage, ChatOptions, ModelInfo
from core.types import LLMResponse, ModelCapability
from core.exceptions import ProviderError

from app.llm.providers.base import BaseLLMProvider


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter provider - gateway to multiple models."""

    @property
    def provider_name(self) -> str:
        return "openrouter"

    @property
    def available_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(
                model_id="anthropic/claude-3.5-sonnet",
                provider="openrouter",
                capabilities={
                    ModelCapability.TEXT,
                    ModelCapability.VISION,
                    ModelCapability.TOOL_CALLING,
                    ModelCapability.REASONING,
                },
                max_tokens=8192,
                cost_per_1k_input=0.003,
                cost_per_1k_output=0.015,
                avg_latency_ms=2000,
                context_window=200_000,
            ),
            ModelInfo(
                model_id="openai/gpt-4o",
                provider="openrouter",
                capabilities={
                    ModelCapability.TEXT,
                    ModelCapability.VISION,
                    ModelCapability.TOOL_CALLING,
                },
                max_tokens=8192,
                cost_per_1k_input=0.005,
                cost_per_1k_output=0.015,
                avg_latency_ms=1500,
                context_window=128_000,
            ),
            ModelInfo(
                model_id="openai/gpt-4o-mini",
                provider="openrouter",
                capabilities={
                    ModelCapability.TEXT,
                    ModelCapability.VISION,
                    ModelCapability.TOOL_CALLING,
                },
                max_tokens=16384,
                cost_per_1k_input=0.00015,
                cost_per_1k_output=0.0006,
                avg_latency_ms=800,
                context_window=128_000,
            ),
            ModelInfo(
                model_id="google/gemini-1.5-pro",
                provider="openrouter",
                capabilities={
                    ModelCapability.TEXT,
                    ModelCapability.VISION,
                    ModelCapability.AUDIO,
                },
                max_tokens=8192,
                cost_per_1k_input=0.00125,
                cost_per_1k_output=0.005,
                avg_latency_ms=1800,
                context_window=1_000_000,
            ),
            ModelInfo(
                model_id="mistralai/mixtral-8x22b",
                provider="openrouter",
                capabilities={
                    ModelCapability.TEXT,
                    ModelCapability.TOOL_CALLING,
                },
                max_tokens=65536,
                cost_per_1k_input=0.0007,
                cost_per_1k_output=0.0024,
                avg_latency_ms=3000,
                context_window=64_000,
            ),
        ]

    @property
    def supports_capabilities(self) -> set[ModelCapability]:
        return {
            ModelCapability.TEXT,
            ModelCapability.VISION,
            ModelCapability.AUDIO,
            ModelCapability.VIDEO,
            ModelCapability.TOOL_CALLING,
            ModelCapability.REASONING,
            ModelCapability.JSON_MODE,
        }

    def _format_message(self, message: ChatMessage) -> dict[str, Any]:
        """Format a chat message for OpenRouter API."""
        content = message.content

        if message.media_url:
            if message.media_url.startswith("data:"):
                content = [
                    {"type": "text", "text": message.content},
                    {"type": "image_url", "image_url": {"url": message.media_url}},
                ]
            else:
                content = [
                    {"type": "text", "text": message.content},
                    {"type": "image_url", "image_url": {"url": message.media_url}},
                ]

        return {"role": message.role, "content": content}

    async def chat(
        self,
        messages: list[ChatMessage],
        options: ChatOptions,
    ) -> LLMResponse:
        """Send a chat completion request to OpenRouter."""
        formatted_messages = [self._format_message(msg) for msg in messages]

        request_data: dict[str, Any] = {
            "model": options.model or "anthropic/claude-3.5-sonnet",
            "messages": formatted_messages,
            "temperature": options.temperature,
        }

        if options.max_tokens:
            request_data["max_tokens"] = options.max_tokens

        if options.tools:
            request_data["tools"] = options.tools
            if options.tool_choice:
                request_data["tool_choice"] = {"type": "function", "function": {"name": options.tool_choice}}

        try:
            data = await self._make_request("POST", "/chat/completions", request_data)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 422:
                raise ProviderError(self.provider_name, "Invalid request parameters")
            raise

        choice = data["choices"][0]
        message = choice["message"]

        tool_calls = None
        if "tool_calls" in message:
            tool_calls = [
                {"name": tc["function"]["name"], "arguments": tc["function"]["arguments"]}
                for tc in message["tool_calls"]
            ]

        reasoning = None
        if "thinking" in message:
            reasoning = message["thinking"]

        sources = []
        if "citations" in data:
            sources = data["citations"]

        usage = data.get("usage", {})

        return LLMResponse(
            content=message.get("content", ""),
            reasoning=reasoning,
            sources=sources,
            tool_calls=tool_calls,
            model=data.get("model", options.model or "unknown"),
            provider=self.provider_name,
            usage={
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
        )

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        options: ChatOptions,
    ) -> AsyncIterator[str]:
        """Send a streaming chat completion request to OpenRouter."""
        formatted_messages = [self._format_message(msg) for msg in messages]

        request_data: dict[str, Any] = {
            "model": options.model or "anthropic/claude-3.5-sonnet",
            "messages": formatted_messages,
            "temperature": options.temperature,
            "stream": True,
        }

        if options.max_tokens:
            request_data["max_tokens"] = options.max_tokens

        if options.tools:
            request_data["tools"] = options.tools

        client = await self._get_client()
        async with client.stream("POST", "/chat/completions", json=request_data) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    if line.strip() == "data: [DONE]":
                        break

                    import json
                    try:
                        chunk = json.loads(line[6:])
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue