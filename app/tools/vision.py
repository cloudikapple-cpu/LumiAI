"""Vision tool for image analysis."""

import base64
import httpx
from typing import Any

import aiofiles

from core.types import TaskType, ToolResult
from app.tools.base import BaseTool, ToolExecutionError


class VisionTool(BaseTool):
    """Tool for analyzing images using vision-capable LLMs."""

    def __init__(self):
        pass

    @property
    def name(self) -> str:
        return "vision"

    @property
    def description(self) -> str:
        return (
            "Analyze images to understand their content. Use this tool when "
            "a user sends a photo and wants to understand, describe, or ask "
            "questions about it. Supports OCR, object detection, scene understanding."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "image_url": {
                    "type": "string",
                    "description": "URL or base64 data of the image to analyze",
                },
                "prompt": {
                    "type": "string",
                    "description": "Question or task about the image",
                },
            },
            "required": ["image_url", "prompt"],
        }

    async def execute(self, parameters: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        """
        Execute vision analysis.

        Args:
            parameters: Must contain 'image_url' and 'prompt'
            context: Execution context with user_id, etc.

        Returns:
            ToolResult with vision analysis
        """
        image_url = parameters.get("image_url")
        prompt = parameters.get("prompt")

        if not image_url:
            return ToolResult(
                success=False,
                data=None,
                error="Missing required parameter: image_url",
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
            image_data = await self._prepare_image_data(image_url)

            analysis_result = {
                "description": f"Image analysis for: {prompt[:100]}...",
                "prompt": prompt,
                "image_size": len(image_data),
                "status": "ready_for_llm",
            }

            return ToolResult(
                success=True,
                data=analysis_result,
                error=None,
                sources=[],
                metadata={
                    "tool": "vision",
                    "image_url": image_url[:200] if len(image_url) > 200 else image_url,
                },
            )

        except Exception as e:
            raise ToolExecutionError(self.name, f"Vision analysis failed: {str(e)}", e)

    async def _prepare_image_data(self, image_url: str) -> str:
        """Prepare image data for LLM (convert to base64 if URL)."""
        if image_url.startswith("data:image"):
            return image_url

        if image_url.startswith(("http://", "https://")):
            client = httpx.AsyncClient(timeout=30.0)
            try:
                response = await client.get(image_url)
                response.raise_for_status()
                content_type = response.headers.get("content-type", "image/jpeg")
                b64_data = base64.b64encode(response.content).decode("utf-8")
                return f"data:{content_type};base64,{b64_data}"
            finally:
                await client.aclose()

        async with aiofiles.open(image_url, "rb") as f:
            content = await f.read()
            b64_data = base64.b64encode(content).decode("utf-8")
            return f"data:image/jpeg;base64,{b64_data}"


class OCRTool(VisionTool):
    """Tool specifically for OCR (Optical Character Recognition)."""

    @property
    def name(self) -> str:
        return "ocr"

    @property
    def description(self) -> str:
        return (
            "Extract text from images using OCR. Use this when the user wants "
            "to read text from a photo, screenshot, or document image."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "image_url": {
                    "type": "string",
                    "description": "URL or base64 data of the image containing text",
                },
                "language": {
                    "type": "string",
                    "description": "Language code (e.g., 'en', 'ru', 'de')",
                    "default": "en",
                },
            },
            "required": ["image_url"],
        }