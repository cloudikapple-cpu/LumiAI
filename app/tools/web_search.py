"""Web search tool using DuckDuckGo or SerpAPI."""

import json
from typing import Any

import httpx

from core.types import TaskType, ToolResult
from app.tools.base import BaseTool, ToolExecutionError


class WebSearchTool(BaseTool):
    """Tool for searching the web."""

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return (
            "Search the web for current information. Use this when you need "
            "up-to-date facts, news, or information about recent events. "
            "Returns top results with brief descriptions and URLs."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return (default: 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        }

    @property
    def supports_ddg(self) -> bool:
        return True

    async def _search_ddg(self, query: str, num_results: int = 5) -> list[dict[str, str]]:
        """Search using DuckDuckGo HTML (no API key required)."""
        client = httpx.AsyncClient(timeout=30.0)
        try:
            response = await client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
            )
            response.raise_for_status()

            results = []
            html = response.text

            import re
            snippet_pattern = re.compile(
                r'<a class="result__a" href="([^"]+)">([^<]+)</a>.*?'
                r'<a class="result__snippet"[^>]*>([^<]+)</a>',
                re.DOTALL,
            )

            for match in snippet_pattern.finditer(html):
                url, title, snippet = match.groups()
                snippet = re.sub(r'<[^>]+>', '', snippet).strip()
                results.append({
                    "url": url,
                    "title": title.strip(),
                    "snippet": snippet,
                })
                if len(results) >= num_results:
                    break

            return results
        finally:
            await client.aclose()

    async def _fetch_content(self, url: str) -> str:
        """Fetch and extract text content from a URL."""
        client = httpx.AsyncClient(timeout=15.0, follow_redirects=True)
        try:
            response = await client.get(url)
            response.raise_for_status()

            html = response.text

            import re
            text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()

            return text[:5000]
        except Exception:
            return ""
        finally:
            await client.aclose()

    async def execute(self, parameters: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        """
        Execute web search.

        Args:
            parameters: Must contain 'query', optionally 'num_results'
            context: Execution context with user_id, etc.

        Returns:
            ToolResult with search results and sources
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

        num_results = parameters.get("num_results", 5)

        try:
            results = await self._search_ddg(query, num_results)

            if not results:
                return ToolResult(
                    success=True,
                    data={"query": query, "results": [], "message": "No results found"},
                    error=None,
                    sources=[],
                    metadata={"method": "ddg"},
                )

            sources = [r["url"] for r in results]

            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "results": results,
                    "count": len(results),
                },
                error=None,
                sources=sources,
                metadata={
                    "method": "ddg",
                    "search_engine": "duckduckgo",
                },
            )

        except Exception as e:
            raise ToolExecutionError(self.name, f"Search failed: {str(e)}", e)


class TavilySearchTool(BaseTool):
    """Tool for searching using Tavily API (more reliable, requires API key)."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or ""
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        return "web_search_tavily"

    @property
    def description(self) -> str:
        return "Search the web using Tavily API for accurate, up-to-date information."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return (default: 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        }

    async def execute(self, parameters: dict[str, Any], context: dict[str, Any]) -> ToolResult:
        """Execute Tavily search."""
        if not self.api_key:
            return ToolResult(
                success=False,
                data=None,
                error="Tavily API key not configured",
                sources=[],
                metadata={},
            )

        query = parameters.get("query")
        if not query:
            return ToolResult(
                success=False,
                data=None,
                error="Missing required parameter: query",
                sources=[],
                metadata={},
            )

        try:
            client = httpx.AsyncClient(timeout=30.0)
            try:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": self.api_key,
                        "query": query,
                        "num_results": parameters.get("num_results", 5),
                        "include_answer": True,
                    },
                )
                response.raise_for_status()
                data = response.json()

                results = [
                    {
                        "url": r["url"],
                        "title": r["title"],
                        "snippet": r["content"],
                    }
                    for r in data.get("results", [])
                ]

                return ToolResult(
                    success=True,
                    data={
                        "query": query,
                        "results": results,
                        "answer": data.get("answer"),
                        "count": len(results),
                    },
                    error=None,
                    sources=[r["url"] for r in results],
                    metadata={
                        "method": "tavily",
                        "search_engine": "tavily",
                    },
                )
            finally:
                await client.aclose()

        except Exception as e:
            raise ToolExecutionError(self.name, f"Tavily search failed: {str(e)}", e)