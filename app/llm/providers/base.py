"""Base classes for LLM providers."""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

import httpx

from core.interfaces import ChatMessage, ChatOptions, LLMProvider, ModelInfo
from core.types import LLMResponse, ModelCapability
from core.exceptions import ProviderError, ProviderTimeoutError, ProviderRateLimitError


class CircuitBreakerOpenError(ProviderError):
    """Raised when circuit breaker is open."""
    pass


class BaseLLMProvider(LLMProvider, ABC):
    """Abstract base class for LLM providers."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        timeout: float = 120.0,
        max_retries: int = 3,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: httpx.AsyncClient | None = None
        self._failure_count = 0
        self._circuit_open = False

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
        return self._client

    async def _close_client(self) -> None:
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _check_circuit_breaker(self) -> None:
        """Check if circuit breaker is open."""
        if self._circuit_open:
            raise CircuitBreakerOpenError(
                self.provider_name,
                f"Circuit breaker is open for {self.provider_name}"
            )

    def _record_success(self) -> None:
        """Record successful request."""
        self._failure_count = 0

    def _record_failure(self) -> None:
        """Record failed request and potentially open circuit."""
        self._failure_count += 1
        if self._failure_count >= 5:
            self._circuit_open = True

    def _reset_circuit_breaker(self) -> None:
        """Reset circuit breaker after cooldown."""
        self._circuit_open = False
        self._failure_count = 0

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider name."""
        pass

    @property
    @abstractmethod
    def available_models(self) -> list[ModelInfo]:
        """List of available models."""
        pass

    @property
    @abstractmethod
    def supports_capabilities(self) -> set[ModelCapability]:
        """Capabilities supported by this provider."""
        pass

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make HTTP request with retry logic."""
        self._check_circuit_breaker()

        client = await self._get_client()
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = await client.request(method, endpoint, json=json_data)
                response.raise_for_status()
                self._record_success()
                return response.json()
            except httpx.TimeoutException as e:
                last_error = e
                if attempt == self.max_retries - 1:
                    raise ProviderTimeoutError(
                        self.provider_name,
                        f"Request timed out after {self.max_retries} attempts"
                    )
except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise ProviderRateLimitError(
                    self.provider_name,
                    "Rate limit exceeded"
                )
                last_error = e
                if attempt == self.max_retries - 1:
                    raise ProviderError(
                        self.provider_name,
                        f"HTTP {e.response.status_code}: {e.response.text[:500]}"
                    )
            except httpx.RequestError as e:
                last_error = e
                if attempt == self.max_retries - 1:
                    raise ProviderError(self.provider_name, str(e))

            if attempt < self.max_retries - 1:
                import asyncio
                await asyncio.sleep(2 ** attempt)

        raise ProviderError(self.provider_name, f"Request failed after {self.max_retries} attempts")

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        options: ChatOptions,
    ) -> LLMResponse:
        """Send a chat completion request."""
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[ChatMessage],
        options: ChatOptions,
    ) -> AsyncIterator[str]:
        """Send a streaming chat completion request."""
        pass

async def healthcheck(self) -> bool:
    """Check provider health."""
    try:
        await self.chat(
            messages=[ChatMessage(role="user", content="ping")],
            options=ChatOptions(model=self.available_models[0].model_id if self.available_models else None, max_tokens=5),
        )
        return True
    except Exception:
        return False