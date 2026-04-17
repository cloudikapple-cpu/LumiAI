"""NVIDIA NIM provider implementation."""

from typing import Any, AsyncIterator

import httpx

from core.interfaces import ChatMessage, ChatOptions, ModelInfo
from core.types import LLMResponse, ModelCapability

from app.llm.providers.base import BaseLLMProvider


class NvidiaNimProvider(BaseLLMProvider):
    """NVIDIA NIM (NVIDIA Inference Microservices) provider."""

    @property
    def provider_name(self) -> str:
        return "nvidia_nim"

    @property
    def available_models(self) -> list[ModelInfo]:
        return [
            ModelInfo(
                model_id="kimi/kimi-k2-thinking",
                provider="nvidia_nim",
                capabilities={
                    ModelCapability.TEXT,
                    ModelCapability.TOOL_CALLING,
                    ModelCapability.REASONING,
                },
                max_tokens=8192,
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                avg_latency_ms=2000,
                context_window=128_000,
            ),
            ModelInfo(
                model_id="minimax/minimax-m2.7",
                provider="nvidia_nim",
                capabilities={
                    ModelCapability.TEXT,
                    ModelCapability.TOOL_CALLING,
                    ModelCapability.REASONING,
                },
                max_tokens=8192,
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                avg_latency_ms=2500,
                context_window=128_000,
            ),
        ]

    @property
    def supports_capabilities(self) -> set[ModelCapability]:
        return {
            ModelCapability.TEXT,
            ModelCapability.TOOL_CALLING,
            ModelCapability.REASONING,
        }

    def _format_message(self, message: ChatMessage) -> dict[str, Any]:
        """Format a chat message for NVIDIA NIM API."""
        return {
            "role": message.role,
            "content": message.content,
        }

    async def chat(
        self,
        messages: list[ChatMessage],
        options: ChatOptions,
    ) -> LLMResponse:
        """Send a chat completion request to NVIDIA NIM."""
        formatted_messages = [self._format_message(msg) for msg in messages]

        request_data: dict[str, Any] = {
            "model": options.model or "minimax/minimax-m2.7",
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
        """Send a streaming chat completion request to NVIDIA NIM."""
        formatted_messages = [self._format_message(msg) for msg in messages]

        request_data: dict[str, Any] = {
            "model": options.model or "minimax/minimax-m2.7",
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
