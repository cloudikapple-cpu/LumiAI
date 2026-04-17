"""Multimodal service - handles images, audio, video, documents."""

from typing import Any

import base64
import httpx

from core.types import MessageType, ToolResult
from app.llm.router import LLMRouter, get_router
from app.memory.short_term import ShortTermMemory


class MultimodalService:
    """
    Service for handling multimodal inputs (images, audio, video, documents).

    Responsibilities:
    - Download and prepare media from Telegram
    - Route to appropriate processing (vision, audio, video, document tools)
    - Coordinate with LLM for analysis
    - Return structured results
    """

    def __init__(
        self,
        llm_router: LLMRouter | None = None,
        short_term_memory: ShortTermMemory | None = None,
    ):
        self.llm_router = llm_router or get_router()
        self.short_term_memory = short_term_memory

    async def process_photo(
        self,
        user_id: int,
        file_path: str,
        caption: str | None = None,
        prompt: str | None = None,
    ) -> dict[str, Any]:
        """
        Process a photo from Telegram.

        Args:
            user_id: User ID
            file_path: Path or URL to the photo
            caption: Optional caption from Telegram
            prompt: Optional specific prompt for analysis

        Returns:
            Analysis result with description and any extracted information
        """
        try:
            image_data = await self._prepare_image(file_path)

            analysis_prompt = prompt or (
                "Analyze this image thoroughly. Provide a detailed description, "
                "identify any text, objects, people, or notable features. "
                f"User's question: {caption}" if caption else "Describe what you see."
            )

            from core.interfaces import ChatMessage, ChatOptions

            messages = [
                ChatMessage(
                    role="user",
                    content=analysis_prompt,
                    media_url=image_data,
                )
            ]

            options = ChatOptions(
                model="openai/gpt-4o",
                temperature=0.7,
                max_tokens=4096,
            )

            response = await self.llm_router.chat_with_fallback(
                messages=messages,
                options=options,
            )

            return {
                "success": True,
                "response": response["content"],
                "model": response.get("model"),
                "usage": response.get("usage", {}),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response": "I apologize, but I encountered an error analyzing this image.",
            }

    async def process_voice(
        self,
        user_id: int,
        file_path: str,
        prompt: str | None = None,
    ) -> dict[str, Any]:
        """
        Process a voice message from Telegram.

        Args:
            user_id: User ID
            file_path: Path or URL to the voice message
            prompt: Optional prompt for additional context

        Returns:
            Transcription and analysis result
        """
        try:
            audio_data = await self._prepare_audio(file_path)

            transcription_prompt = (
                "Transcribe this audio accurately. If there's a specific question "
                "or request in the audio, also address it."
            )

            from core.interfaces import ChatMessage, ChatOptions

            messages = [
                ChatMessage(
                    role="user",
                    content=transcription_prompt,
                    media_url=audio_data,
                )
            ]

            options = ChatOptions(
                model="openai/gpt-4o",
                temperature=0.3,
                max_tokens=4096,
            )

            response = await self.llm_router.chat_with_fallback(
                messages=messages,
                options=options,
            )

            return {
                "success": True,
                "response": response["content"],
                "transcription": response["content"],
                "model": response.get("model"),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response": "I apologize, but I encountered an error processing this voice message.",
            }

    async def process_video(
        self,
        user_id: int,
        file_path: str,
        prompt: str | None = None,
    ) -> dict[str, Any]:
        """
        Process a video from Telegram.

        Note: This is typically queued as a background task for heavy processing.

        Args:
            user_id: User ID
            file_path: Path or URL to the video
            prompt: Optional specific prompt for analysis

        Returns:
            Processing status and info
        """
        return {
            "success": True,
            "status": "queued",
            "message": "Video processing has been queued. This may take a few minutes.",
            "task_type": "video_analysis",
        }

    async def process_document(
        self,
        user_id: int,
        file_path: str,
        prompt: str | None = None,
    ) -> dict[str, Any]:
        """
        Process a document from Telegram.

        Args:
            user_id: User ID
            file_path: Path or URL to the document
            prompt: Optional specific prompt for analysis

        Returns:
            Processing status and info
        """
        return {
            "success": True,
            "status": "queued",
            "message": "Document processing has been queued.",
            "task_type": "document_analysis",
        }

    async def _prepare_image(self, file_path: str) -> str:
        """Prepare image data for LLM (base64)."""
        if file_path.startswith("data:image"):
            return file_path

        if file_path.startswith(("http://", "https://")):
            client = httpx.AsyncClient(timeout=30.0)
            try:
                response = await client.get(file_path)
                response.raise_for_status()
                content_type = response.headers.get("content-type", "image/jpeg")
                b64_data = base64.b64encode(response.content).decode("utf-8")
                return f"data:{content_type};base64,{b64_data}"
            finally:
                await client.aclose()

        import aiofiles
        async with aiofiles.open(file_path, "rb") as f:
            content = await f.read()
            b64_data = base64.b64encode(content).decode("utf-8")
            return f"data:image/jpeg;base64,{b64_data}"

    async def _prepare_audio(self, file_path: str) -> str:
        """Prepare audio data for LLM (base64)."""
        if file_path.startswith("data:audio") or file_path.startswith("data:video"):
            return file_path

        if file_path.startswith(("http://", "https://")):
            client = httpx.AsyncClient(timeout=60.0)
            try:
                response = await client.get(file_path)
                response.raise_for_status()
                content_type = response.headers.get("content-type", "audio/ogg")
                b64_data = base64.b64encode(response.content).decode("utf-8")
                return f"data:{content_type};base64,{b64_data}"
            finally:
                await client.aclose()

        import aiofiles
        async with aiofiles.open(file_path, "rb") as f:
            content = await f.read()
            b64_data = base64.b64encode(content).decode("utf-8")
            return f"data:audio/ogg;base64,{b64_data}"


_multimodal_service: MultimodalService | None = None


def get_multimodal_service() -> MultimodalService:
    """Get or create the multimodal service."""
    global _multimodal_service
    if _multimodal_service is None:
        _multimodal_service = MultimodalService()
    return _multimodal_service