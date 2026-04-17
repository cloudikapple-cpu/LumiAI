"""Long-term memory using PostgreSQL."""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserMemory
from app.db.repositories.memory_repo import MemoryRepository


class LongTermMemory:
    """
    Long-term memory using PostgreSQL.
    Stores user preferences, important facts, and historical information.
    """

    CATEGORY_PREFERENCE = "preference"
    CATEGORY_FACT = "fact"
    CATEGORY_HISTORY = "history"
    CATEGORY_SUMMARY = "summary"

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = MemoryRepository(session)

    async def store_preference(
        self,
        user_id: int,
        key: str,
        value: str,
        importance: int = 2,
    ) -> UserMemory:
        """Store a user preference."""
        return await self.repo.add_memory(
            user_id=user_id,
            category=self.CATEGORY_PREFERENCE,
            key=key,
            value=value,
            importance=importance,
        )

    async def store_fact(
        self,
        user_id: int,
        key: str,
        value: str,
        importance: int = 3,
        ttl_seconds: int | None = None,
    ) -> UserMemory:
        """Store an important fact about the user."""
        return await self.repo.add_memory(
            user_id=user_id,
            category=self.CATEGORY_FACT,
            key=key,
            value=value,
            importance=importance,
            ttl_seconds=ttl_seconds,
        )

    async def store_conversation_summary(
        self,
        user_id: int,
        summary: str,
    ) -> UserMemory:
        """Store a summary of a conversation for future reference."""
        return await self.repo.add_memory(
            user_id=user_id,
            category=self.CATEGORY_SUMMARY,
            key=f"summary_{datetime.utcnow().timestamp()}",
            value=summary,
            importance=1,
            ttl_seconds=30 * 24 * 3600,
        )

    async def get_preference(self, user_id: int, key: str) -> str | None:
        """Get a user preference by key."""
        memory = await self.repo.get_memory(user_id, f"{self.CATEGORY_PREFERENCE}:{key}")
        if not memory:
            memory = await self.repo.get_memory(user_id, key)
        return memory.value if memory else None

    async def get_all_preferences(self, user_id: int) -> dict[str, str]:
        """Get all user preferences."""
        memories = await self.repo.get_memories_by_category(
            user_id, self.CATEGORY_PREFERENCE
        )
        return {m.key: m.value for m in memories}

    async def search_facts(self, user_id: int, query: str) -> list[UserMemory]:
        """Search for facts related to a query."""
        return await self.repo.search_memories(user_id, query)

    async def get_recent_facts(self, user_id: int, limit: int = 10) -> list[UserMemory]:
        """Get recent important facts."""
        return await self.repo.get_memories_by_category(user_id, self.CATEGORY_FACT, limit)

    async def get_context_for_user(self, user_id: int, query: str | None = None) -> str:
        """
        Build a context string from user's long-term memory.
        Used to augment prompts with user information.
        """
        memories = await self.repo.get_all_memories(user_id, limit=20)

        if not memories:
            return ""

        context_parts = []
        for memory in memories:
            if memory.importance >= 2:
                context_parts.append(f"[{memory.category}/{memory.key}]: {memory.value}")

        if context_parts:
            return "User context:\n" + "\n".join(context_parts)
        return ""

    async def forget_user(self, user_id: int) -> int:
        """Delete all memories for a user. Returns count of deleted memories."""
        return await self.repo.delete_all_memories(user_id)

    async def forget_last_dialog(self, user_id: int) -> None:
        """Forget information about the last conversation."""
        memories = await self.repo.get_memories_by_category(user_id, self.CATEGORY_SUMMARY)
        for memory in memories:
            await self.session.delete(memory)
        await self.session.flush()

    async def get_memory_summary(self, user_id: int) -> dict[str, Any]:
        """Get a summary of user's memory storage."""
        return await self.repo.get_memory_summary(user_id)


async def get_long_term_memory(session: AsyncSession) -> LongTermMemory:
    """Create LongTermMemory instance."""
    return LongTermMemory(session)