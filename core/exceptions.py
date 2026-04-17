"""Custom exceptions for the application."""


class LumiAIException(Exception):
    """Base exception for all LumiAI errors."""

    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ConfigurationError(LumiAIException):
    """Raised when configuration is invalid or missing."""


class ProviderError(LumiAIException):
    """Raised when an LLM provider fails."""

    def __init__(self, provider: str, message: str, details: dict | None = None):
        self.provider = provider
        super().__init__(f"[{provider}] {message}", details)


class ProviderTimeoutError(ProviderError):
    """Raised when a provider times out."""
    pass


class ProviderRateLimitError(ProviderError):
    """Raised when a provider rate limits."""
    pass


class CircuitBreakerOpenError(ProviderError):
    """Raised when circuit breaker is open."""
    pass


class ToolError(LumiAIException):
    """Raised when a tool execution fails."""

    def __init__(self, tool: str, message: str, details: dict | None = None):
        self.tool = tool
        super().__init__(f"[{tool}] {message}", details)


class WebSearchError(ToolError):
    """Raised when web search fails."""
    pass


class MediaProcessingError(ToolError):
    """Raised when media processing fails."""
    pass


class StorageError(LumiAIException):
    """Raised when storage operations fail."""
    pass


class DatabaseError(LumiAIException):
    """Raised when database operations fail."""
    pass


class RateLimitError(LumiAIException):
    """Raised when user hits rate limit."""
    pass


class AntiSpamError(LumiAIException):
    """Raised when user is flagged as spammer."""
    pass


class MemoryError(LumiAIException):
    """Raised when memory operations fail."""
    pass


class ValidationError(LumiAIException):
    """Raised when input validation fails."""
    pass