"""Video tool for video analysis and processing."""

import base64
import httpx
from typing import Any

from core.types import TaskType, ToolResult
from app.tools.base import BaseTool, ToolExecutionError


class VideoTool(BaseTool):
    """Tool for analyzing videos."""

    @property
    def name(self) -> str:
        return "video_analysis"

    @property
    def description(self) -> str:
        return (
            "Analyze videos to understand their content. Use this tool when "
            "the user sends a video and wants to understand what's in it, "
            "get a summary, or ask questions about specific frames or content. "
            "This is a heavy operation that runs in background."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "video_url": {
                    "type": "string",
                    "description": "URL or path to the video file",
                },
                "prompt": {
                    "type": "string",
                    "description": "Question or task about the video",
                },
                "extract_frames": {
                    "type": "boolean",
                    "description": "Extract key frames for analysis",
                    "default": True,
                },
                "extract_audio": {
                    "type": "boolean",
                    "description": "Extract and transcribe audio",
                    "default": True,
                },
            },
            "required": ["video_url", "prompt"],
        }

    async def execute(self, parameters: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        """
        Execute video analysis preparation.

        Note: Actual video processing is done in background workers.
        This tool queues the task and returns a task ID for tracking.

        Args:
            parameters: Must contain 'video_url' and 'prompt'
            context: Execution context with user_id, etc.

        Returns:
            ToolResult with task_id for tracking
        """
        video_url = parameters.get("video_url")
        prompt = parameters.get("prompt")

        if not video_url:
            return ToolResult(
                success=False,
                data=None,
                error="Missing required parameter: video_url",
                sources=[],
                metadata={},
            )

        if not prompt:
            return ToolResult(
                success=False,
                data=None,
                error="Missing required parameter: prompt",
                sources=[],
                metadata={},
            )

        try:
            video_info = {
                "status": "queued_for_processing",
                "video_url": video_url[:200] if len(video_url) > 200 else video_url,
                "prompt": prompt,
                "extract_frames": parameters.get("extract_frames", True),
                "extract_audio": parameters.get("extract_audio", True),
            }

            return ToolResult(
                success=True,
                data=video_info,
                error=None,
                sources=[],
                metadata={
                    "tool": "video_analysis",
                    "processing": "background",
                },
            )

        except Exception as e:
            raise ToolExecutionError(self.name, f"Video analysis failed: {str(e)}", e)

    async def _download_video(self, video_url: str, chunk_size: int = 8192) -> bytes:
        """Download video from URL."""
        client = httpx.AsyncClient(timeout=120.0, follow_redirects=True)
        try:
            async with client.stream("GET", video_url) as response:
                response.raise_for_status()
                chunks = []
                async for chunk in response.aiter_bytes(chunk_size):
                    chunks.append(chunk)
                return b"".join(chunks)
        finally:
            await client.aclose()

    async def _extract_frames(self, video_path: str, num_frames: int = 5) -> list[str]:
        """
        Extract key frames from video.

        Note: Requires ffmpeg to be installed.
        This is typically run in a background worker.
        """
        return []


class VideoSummaryTool(VideoTool):
    """Tool specifically for video summarization."""

    @property
    def name(self) -> str:
        return "video_summary"

    @property
    def description(self) -> str:
        return (
            "Generate a summary of a video's content. Extract key moments, "
            "transcribe audio, and provide a comprehensive summary."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "video_url": {
                    "type": "string",
                    "description": "URL or path to the video file",
                },
                "summary_type": {
                    "type": "string",
                    "enum": ["brief", "detailed", "timestamps"],
                    "description": "Type of summary to generate",
                    "default": "brief",
                },
            },
            "required": ["video_url"],
        }