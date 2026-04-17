"""RAG (Retrieval-Augmented Generation) tool for memory search."""

from typing import Any

from core.types import TaskType, ToolResult
from app.tools.base import BaseTool, ToolExecutionError


class RAGTool(BaseTool):
    """Tool for RAG-based search over user memory and documents."""

    def __init__(self):
        pass

    @property
    def name(self) -> str:
        return "rag"

    @property
    def description(self) -> str:
        return (
            "Search and retrieve information from user's long-term memory. "
            "Use this to find relevant facts, preferences, or previous "
            "conversations when the user asks about something personal "
            "or requests information that was discussed before."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query to find relevant information",
                },
                "memory_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Types of memory to search (preferences, facts, history)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results",
                    "default": 5,
                },
            },
            "required": ["query"],
        }

    async def execute(self, parameters: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        """
        Execute RAG search over user memory.

        Args:
            parameters: Must contain 'query', optionally 'memory_types' and 'limit'
            context: Execution context with user_id, conversation_id, etc.

        Returns:
            ToolResult with retrieved context
        """
        query = parameters.get("query")
        if not query:
            return ToolResult(
                success=False,
                data=None,
                error="Missing required parameter: query",
                sources=[],
                metadata={},
            )

        user_id = context.get("user_id")
        if not user_id:
            return ToolResult(
                success=False,
                data=None,
                error="Missing user_id in context",
                sources=[],
                metadata={},
            )

        try:
            memories = await self._search_memories(
                user_id=user_id,
                query=query,
                memory_types=parameters.get("memory_types"),
                limit=parameters.get("limit", 5),
            )

            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "results": memories,
                    "count": len(memories),
                },
                error=None,
                sources=[],
                metadata={
                    "tool": "rag",
                    "user_id": user_id,
                },
            )

        except Exception as e:
            raise ToolExecutionError(self.name, f"RAG search failed: {str(e)}", e)

    async def _search_memories(
        self,
        user_id: int,
        query: str,
        memory_types: list[str] | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Search user memories.

        Note: In production, this should use proper embedding similarity search.
        For now, it does keyword matching via the memory repository.
        """
        from app.db.repositories.memory_repo import MemoryRepository
        from app.db.base import acquire_session

        async with acquire_session() as session:
            repo = MemoryRepository(session)

            if memory_types:
                results = []
                for mem_type in memory_types:
                    type_results = await repo.get_memories_by_category(user_id, mem_type, limit)
                    results.extend(type_results)
            else:
                results = await repo.search_memories(user_id, query, limit)

            return [
                {
                    "key": r.key,
                    "category": r.category,
                    "value": r.value,
                    "importance": r.importance,
                }
                for r in results
            ]


class FactCheckTool(BaseTool):
    """Tool for verifying facts against user's known information."""

    @property
    def name(self) -> str:
        return "fact_check"

    @property
    def description(self) -> str:
        return (
            "Verify facts against the user's previously known information. "
            "Use this to check if a statement contradicts what the user "
            "has previously told the assistant."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "statements": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Statements to verify",
                },
            },
            "required": ["statements"],
        }

    async def execute(self, parameters: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        """Execute fact check against user memory."""
        statements = parameters.get("statements", [])
        user_id = context.get("user_id")

        if not statements:
            return ToolResult(
                success=False,
                data=None,
                error="Missing required parameter: statements",
                sources=[],
                metadata={},
            )

        if not user_id:
            return ToolResult(
                success=False,
                data=None,
                error="Missing user_id in context",
                sources=[],
                metadata={},
            )

        return ToolResult(
            success=True,
            data={
                "statements": statements,
                "verifications": [],
                "message": "Fact check placeholder",
            },
            error=None,
            sources=[],
            metadata={
                "tool": "fact_check",
            },
        )