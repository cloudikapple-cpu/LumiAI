"""Document tool for processing PDFs, text files, etc."""

from typing import Any

from core.types import TaskType, ToolResult
from app.tools.base import BaseTool, ToolExecutionError


class DocumentTool(BaseTool):
    """Tool for processing documents (PDF, txt, docx, etc.)."""

    def __init__(self):
        pass

    @property
    def name(self) -> str:
        return "document_analysis"

    @property
    def description(self) -> str:
        return (
            "Analyze documents (PDF, text files, Word documents) to extract "
            "their content and answer questions about them. Use this when the "
            "user sends a document and wants to understand, summarize, or "
            "ask questions about its contents."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "document_url": {
                    "type": "string",
                    "description": "URL or path to the document file",
                },
                "prompt": {
                    "type": "string",
                    "description": "Question or task about the document",
                },
                "extract_text": {
                    "type": "boolean",
                    "description": "Extract text from document",
                    "default": True,
                },
            },
            "required": ["document_url"],
        }

    async def execute(self, parameters: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        """
        Execute document analysis preparation.

        Args:
            parameters: Must contain 'document_url', optionally 'prompt'
            context: Execution context with user_id, etc.

        Returns:
            ToolResult with document processing info
        """
        document_url = parameters.get("document_url")
        if not document_url:
            return ToolResult(
                success=False,
                data=None,
                error="Missing required parameter: document_url",
                sources=[],
                metadata={},
            )

        try:
            file_ext = self._get_file_extension(document_url)
            content_type = self._get_content_type(file_ext)

            document_info = {
                "status": "ready_for_processing",
                "document_url": document_url[:200] if len(document_url) > 200 else document_url,
                "file_type": file_ext,
                "content_type": content_type,
                "prompt": parameters.get("prompt", "Summarize and analyze this document"),
                "extract_text": parameters.get("extract_text", True),
            }

            return ToolResult(
                success=True,
                data=document_info,
                error=None,
                sources=[],
                metadata={
                    "tool": "document_analysis",
                    "file_type": file_ext,
                },
            )

        except Exception as e:
            raise ToolExecutionError(self.name, f"Document processing failed: {str(e)}", e)

    def _get_file_extension(self, url: str) -> str:
        """Extract file extension from URL or path."""
        if "." in url:
            return url.rsplit(".", 1)[-1].lower().split("?")[0]
        return "unknown"

    def _get_content_type(self, extension: str) -> str:
        """Get MIME content type from extension."""
        content_types = {
            "pdf": "application/pdf",
            "txt": "text/plain",
            "doc": "application/msword",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "rtf": "application/rtf",
            "md": "text/markdown",
            "json": "application/json",
            "csv": "text/csv",
        }
        return content_types.get(extension, "application/octet-stream")


class PDFTool(DocumentTool):
    """Tool specifically for PDF processing."""

    @property
    def name(self) -> str:
        return "pdf_analysis"

    @property
    def description(self) -> str:
        return "Extract and analyze content from PDF documents."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "document_url": {
                    "type": "string",
                    "description": "URL or path to the PDF file",
                },
                "pages": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Specific pages to extract (empty for all)",
                },
                "prompt": {
                    "type": "string",
                    "description": "Question about the PDF content",
                },
            },
            "required": ["document_url"],
        }


class TextFileTool(DocumentTool):
    """Tool specifically for plain text files."""

    @property
    def name(self) -> str:
        return "text_file_analysis"

    @property
    def description(self) -> str:
        return "Read and analyze plain text files."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "document_url": {
                    "type": "string",
                    "description": "URL or path to the text file",
                },
                "prompt": {
                    "type": "string",
                    "description": "Question about the text content",
                },
                "encoding": {
                    "type": "string",
                    "description": "Text encoding",
                    "default": "utf-8",
                },
            },
            "required": ["document_url"],
        }