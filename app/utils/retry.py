"""Retry utilities with exponential backoff."""

import asyncio
import time
from functools import wraps
from typing import Any, Callable, TypeVar

from core.exceptions import ProviderError, ProviderTimeoutError


T = TypeVar("T")


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    retriable_exceptions: tuple = (ProviderError, ProviderTimeoutError, asyncio.TimeoutError),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retrying async functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff calculation
        retriable_exceptions: Tuple of exceptions that trigger retry

    Usage:
        @retry_with_backoff(max_retries=3)
        async def my_function():
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retriable_exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        delay = min(base_delay * (exponential_base**attempt), max_delay)

                        if isinstance(e, ProviderTimeoutError):
                            delay *= 0.5

                        await asyncio.sleep(delay)
                    else:
                        raise

            if last_exception:
                raise last_exception

        return wrapper

    return decorator


def retry_sync(
    max_retries: int = 3,
    base_delay: float = 1.0,
    exponential_base: float = 2.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retrying sync functions with exponential backoff.

    Use this for non-async functions.
    """

def decorator(func: Callable[..., T]) -> Callable[..., T]:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        last_exception: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                if attempt < max_retries:
                    delay = min(base_delay * (exponential_base**attempt), 60.0)
                    time.sleep(delay)
                else:
                    raise

            if last_exception:
                raise last_exception

        return wrapper

    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    Prevents repeated calls to a failing service.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self._failure_count = 0
        self._last_failure_time: float | None = None
        self._state = "closed"

    @property
    def state(self) -> str:
        """Get current circuit breaker state."""
        if self._state == "open":
            if self._last_failure_time:
                if time.time() - self._last_failure_time >= self.recovery_timeout:
                    self._state = "half-open"
                    return "half-open"
        return self._state

    def record_success(self) -> None:
        """Record a successful call."""
        self._failure_count = 0
        self._state = "closed"

    def record_failure(self) -> None:
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self.failure_threshold:
            self._state = "open"

    def can_execute(self) -> bool:
        """Check if a call can be executed."""
        return self.state != "open"

    async def __call__(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute function with circuit breaker protection."""
        if not self.can_execute():
            raise CircuitBreakerOpen("Circuit breaker is open")

        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except self.expected_exception as e:
            self.record_failure()
            raise


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""
    pass