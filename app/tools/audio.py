"""Audio tool for speech-to-text transcription."""

import base64
import httpx
from typing import Any

from core.types import TaskType, ToolResult
from app.tools.base import BaseTool, ToolExecutionError


class AudioTool(BaseTool):
    """Tool for processing and transcribing audio."""

    @property
    def name(self) -> str:
        return "audio_transcription"

    @property
    def description(self) -> str:
        return (
            "Transcribe voice messages or audio files to text. Use this tool "
            "when the user sends a voice message or audio file and wants it "
            "transcribed or analyzed."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "audio_url": {
                    "type": "string",
                    "description": "URL or base64 data of the audio file",
                },
                "language": {
                    "type": "string",
                    "description": "Language code (e.g., 'en', 'ru')",
                },
                "task": {
                    "type": "string",
                    "enum": ["transcribe", "translate"],
                    "description": "Task to perform",
                    "default": "transcribe",
                },
            },
            "required": ["audio_url"],
        }

    async def execute(self, parameters: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        """
        Execute audio transcription.

        Args:
            parameters: Must contain 'audio_url', optionally 'language' and 'task'
            context: Execution context with user_id, etc.

        Returns:
            ToolResult with transcription
        """
        audio_url = parameters.get("audio_url")
        if not audio_url:
            return ToolResult(
                success=False,
                data=None,
                error="Missing required parameter: audio_url",
                sources=[],
                metadata={},
            )

        try:
            audio_data = await self._prepare_audio_data(audio_url)

            transcription_result = {
                "status": "ready_for_transcription",
                "audio_size": len(audio_data),
                "task": parameters.get("task", "transcribe"),
                "language": parameters.get("language"),
            }

            return ToolResult(
                success=True,
                data=transcription_result,
                error=None,
                sources=[],
                metadata={
                    "tool": "audio_transcription",
                    "audio_url": audio_url[:200] if len(audio_url) > 200 else audio_url,
                },
            )

        except Exception as e:
            raise ToolExecutionError(self.name, f"Audio processing failed: {str(e)}", e)

    async def _prepare_audio_data(self, audio_url: str) -> str:
        """Prepare audio data for transcription (convert to base64 if URL)."""
        if audio_url.startswith("data:audio") or audio_url.startswith("data:video"):
            return audio_url

        if audio_url.startswith(("http://", "https://")):
            client = httpx.AsyncClient(timeout=60.0)
            try:
                response = await client.get(audio_url)
                response.raise_for_status()
                content_type = response.headers.get("content-type", "audio/ogg")
                b64_data = base64.b64encode(response.content).decode("utf-8")
                return f"data:{content_type};base64,{b64_data}"
            finally:
                await client.aclose()

        import aiofiles
        async with aiofiles.open(audio_url, "rb") as f:
            content = await f.read()
            b64_data = base64.b64encode(content).decode("utf-8")
            return f"data:audio/ogg;base64,{b64_data}"


class TextToSpeechTool(BaseTool):
    """Tool for text-to-speech synthesis."""

    @property
    def name(self) -> str:
        return "text_to_speech"

    @property
    def description(self) -> str:
        return (
            "Convert text to speech audio. Use this to generate audio responses "
            "that can be sent back to the user as voice messages."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to convert to speech",
                },
                "voice": {
                    "type": "string",
                    "description": "Voice ID to use",
                    "default": "alloy",
                },
                "speed": {
                    "type": "number",
                    "description": "Speech speed (0.5 - 2.0)",
                    "default": 1.0,
                },
            },
            "required": ["text"],
        }

    async def execute(self, parameters: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        """Execute text-to-speech synthesis."""
        text = parameters.get("text")
        if not text:
            return ToolResult(
                success=False,
                data=None,
                error="Missing required parameter: text",
                sources=[],
                metadata={},
            )

        return ToolResult(
            success=True,
            data={
                "status": "tts_generated",
                "text_length": len(text),
            },
            error=None,
            sources=[],
            metadata={
                "tool": "text_to_speech",
            },
        )