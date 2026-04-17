"""Type definitions for the application."""

from enum import Enum
from typing import Any, Literal, TypedDict

MessageType = Literal["text", "photo", "voice", "video", "document", "unknown"]


class ModelCapability(str, Enum):
    TEXT = "text"
    VISION = "vision"
    AUDIO = "audio"
    VIDEO = "video"
    TOOL_CALLING = "tool_calling"
    REASONING = "reasoning"
    JSON_MODE = "json_mode"


class TaskType(str, Enum):
    CHAT = "chat"
    CODE = "code"
    VISION_ANALYSIS = "vision_analysis"
    AUDIO_TRANSCRIPTION = "audio_transcription"
    VIDEO_ANALYSIS = "video_analysis"
    DOCUMENT_ANALYSIS = "document_analysis"
    WEB_SEARCH = "web_search"
    RAG = "rag"
    MIXED = "mixed"


class ResponseMode(str, Enum):
    STREAM = "stream"
    BULK = "bulk"
    SPLIT = "split"


class UserMode(str, Enum):
    ASSISTANT = "assistant"
    EXPLORER = "explorer"  # Deep research, more web search
    CONCISE = "concise"    # Short answers


class DialogTurn(TypedDict):
    role: Literal["user", "assistant", "system"]
    content: str
    media_url: str | None


class ToolResult(TypedDict, total=False):
    success: bool
    data: Any
    error: str | None
    sources: list[str]
    metadata: dict[str, Any]


class LLMResponse(TypedDict):
    content: str
    reasoning: str | None
    sources: list[str]
    tool_calls: list[dict[str, Any]] | None
    model: str
    provider: str
    usage: dict[str, int]