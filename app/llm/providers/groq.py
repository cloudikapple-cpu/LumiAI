"""Groq provider implementation."""

from typing import Any, AsyncIterator

import httpx

from core.interfaces import ChatMessage, ChatOptions, ModelInfo
from core.types import LLMResponse, ModelCapability

from app.llm.providers.base import BaseLLMProvider


class GroqProvider(BaseLLMProvider):
    """Groq provider - fast inference for text tasks."""

    @property
    def provider_name(self) -> str:
        return "groq"

    @property
    def available_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(
                model_id="llama-3.1-70b-versatile",
                provider="groq",
                capabilities={
                    ModelCapability.TEXT,
                    ModelCapability.TOOL_CALLING,
                },
                max_tokens=8192,
                cost_per_1k_input=0.0007,
                cost_per_1k_output=0.0024,
                avg_latency_ms=400,
                context_window=128_000,
            ),
            ModelInfo(
                model_id="llama-3.1-8b-instant",
                provider="groq",
                capabilities={
                    ModelCapability.TEXT,
                },
                max_tokens=8192,
                cost_per_1k_input=0.00005,
                cost_per_1k_output=0.00008,
                avg_latency_ms=200,
                context_window=128_000,
            ),
            ModelInfo(
                model_id="mixtral-8x7b-32768",
                provider="groq",
                capabilities={
                    ModelCapability.TEXT,
                },
                max_tokens=32768,
                cost_per_1k_input=0.00024,
                cost_per_1k_output=0.00024,
                avg_latency_ms=600,
                context_window=32768,
            ),
        ]

    @property
    def supports_capabilities(self) -> set[ModelCapability]:
        return {
            ModelCapability.TEXT,
            ModelCapability.TOOL_CALLING,
        }

    def _format_message(self, message: ChatMessage) -> dict[str, Any]:
        """Format a chat message for Groq API."""
        return {
            "role": message.role,
            "content": message.content,
        }

    async def chat(
        self,
        messages: list[ChatMessage],
        options: ChatOptions,
    ) -> LLMResponse:
        """Send a chat completion request to Groq."""
        formatted_messages = [self._format_message(msg) for msg in messages]

        request_data: dict[str, Any] = {
            "model": options.model or "llama-3.1-70b-versatile",
            "messages": formatted_messages,
            "temperature": options.temperature,
            "stream": False,
        }

        if options.max_tokens:
            request_data["max_tokens"] = options.max_tokens

        if options.tools:
            request_data["tools"] = options.tools

        data = await self._make_request("POST", "/chat/completions", request_data)

        choice = data["choices"][0]
        message = choice["message"]

        tool_calls = None
        if "tool_calls" in message:
            tool_calls = [
                {"name": tc["function"]["name"], "arguments": tc["function"]["arguments"]}
                for tc in message["tool_calls"]
            ]

        usage = data.get("usage", {})

        return LLMResponse(
            content=message.get("content", ""),
            reasoning=None,
            sources=[],
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
        """Send a streaming chat completion request to Groq."""
        formatted_messages = [self._format_message(msg) for msg in messages]

        request_data: dict[str, Any] = {
            "model": options.model or "llama-3.1-70b-versatile",
            "messages": formatted_messages,
            "temperature": options.temperature,
            "stream": True,
        }

        if options.max_tokens:
            request_data["max_tokens"] = options.max_tokens

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
