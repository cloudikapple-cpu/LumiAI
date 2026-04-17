"""Memory repository for user memory operations."""

from datetime import datetime

from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserMemory


class MemoryRepository:
    """Repository for user memory operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_memory(
        self,
        user_id: int,
        category: str,
        key: str,
        value: str,
        importance: int = 1,
        ttl_seconds: int | None = None,
    ) -> UserMemory:
        """Add a new memory entry."""
        expires_at = None
        if ttl_seconds:
            expires_at = datetime.utcnow().timestamp() + ttl_seconds
            expires_at = datetime.fromtimestamp(expires_at)

        memory = UserMemory(
            user_id=user_id,
            category=category,
            key=key,
            value=value,
            importance=importance,
            expires_at=expires_at,
        )
        self.session.add(memory)
        await self.session.flush()
        return memory

    async def get_memory(self, user_id: int, key: str) -> UserMemory | None:
        """Get a specific memory by key."""
        result = await self.session.execute(
            select(UserMemory).where(
                and_(
                    UserMemory.user_id == user_id,
                    UserMemory.key == key,
                    UserMemory.expires_at.is_(None) | (UserMemory.expires_at > datetime.utcnow()),
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_memories_by_category(
        self, user_id: int, category: str, limit: int = 50
    ) -> list[UserMemory]:
        """Get all memories in a category."""
        result = await self.session.execute(
            select(UserMemory)
            .where(
                and_(
                    UserMemory.user_id == user_id,
                    UserMemory.category == category,
                    UserMemory.expires_at.is_(None) | (UserMemory.expires_at > datetime.utcnow()),
                )
            )
            .order_by(UserMemory.importance.desc(), UserMemory.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_all_memories(self, user_id: int, limit: int = 100) -> list[UserMemory]:
        """Get all active memories for a user."""
        result = await self.session.execute(
            select(UserMemory)
            .where(
                and_(
                    UserMemory.user_id == user_id,
                    UserMemory.expires_at.is_(None) | (UserMemory.expires_at > datetime.utcnow()),
                )
            )
            .order_by(UserMemory.importance.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def search_memories(self, user_id: int, query: str, limit: int = 10) -> list[UserMemory]:
        """Search memories by content."""
        result = await self.session.execute(
            select(UserMemory)
            .where(
                and_(
                    UserMemory.user_id == user_id,
                    UserMemory.value.ilike(f"%{query}%"),
                    UserMemory.expires_at.is_(None) | (UserMemory.expires_at > datetime.utcnow()),
                )
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete_memory(self, user_id: int, key: str) -> bool:
        """Delete a specific memory."""
        result = await self.session.execute(
            delete(UserMemory).where(
                and_(UserMemory.user_id == user_id, UserMemory.key == key)
            )
        )
        await self.session.flush()
        return result.rowcount > 0

    async def delete_all_memories(self, user_id: int) -> int:
        """Delete all memories for a user."""
        result = await self.session.execute(
            delete(UserMemory).where(UserMemory.user_id == user_id)
        )
        await self.session.flush()
        return result.rowcount

    async def delete_expired(self) -> int:
        """Delete all expired memories."""
        result = await self.session.execute(
            delete(UserMemory).where(
                UserMemory.expires_at.is_not(None),
                UserMemory.expires_at <= datetime.utcnow(),
            )
        )
        await self.session.flush()
        return result.rowcount

    async def update_memory(
        self, user_id: int, key: str, value: str, importance: int | None = None
    ) -> UserMemory | None:
        """Update a memory's value."""
        memory = await self.get_memory(user_id, key)
        if memory:
            memory.value = value
            if importance is not None:
                memory.importance = importance
            memory.updated_at = datetime.utcnow()
            await self.session.flush()
        return memory

    async def get_memory_summary(self, user_id: int) -> dict:
        """Get a summary of user's memories."""
        memories = await self.get_all_memories(user_id, limit=100)

        categories: dict[str, int] = {}
        for memory in memories:
            categories[memory.category] = categories.get(memory.category, 0) + 1

        return {
            "total": len(memories),
            "by_category": categories,
            "high_importance": sum(1 for m in memories if m.importance >= 3),
        }