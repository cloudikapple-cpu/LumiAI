"""Short-term memory using Redis."""

import json
from datetime import timedelta
from typing import Any

import redis.asyncio as redis

from app.config import settings
from core.types import DialogTurn


class ShortTermMemory:
    """
    Short-term memory using Redis for fast access.
    Stores current conversation context, session state, and temporary data.
    """

    DIALOG_PREFIX = "dialog:"
    SESSION_PREFIX = "session:"
    RATE_LIMIT_PREFIX = "ratelimit:"
    TASK_PREFIX = "task:"

    DEFAULT_TTL = 3600  # 1 hour
    DIALOG_TTL = 1800  # 30 minutes
    SESSION_TTL = 86400  # 24 hours

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def add_dialog_message(
        self,
        user_id: int,
        role: str,
        content: str,
        media_url: str | None = None,
    ) -> int:
        """Add a message to the user's current dialog."""
        key = f"{self.DIALOG_PREFIX}{user_id}"
        message = json.dumps({
            "role": role,
            "content": content,
            "media_url": media_url,
        })

        pipe = self.redis.pipeline()
        pipe.rpush(key, message)
        pipe.expire(key, self.DIALOG_TTL)
        results = await pipe.execute()
        return results[0]

    async def get_dialog(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DialogTurn]:
        """Get recent dialog messages for a user."""
        key = f"{self.DIALOG_PREFIX}{user_id}"
        messages = await self.redis.lrange(key, offset, offset + limit - 1)
        return [json.loads(m) for m in messages]

    async def clear_dialog(self, user_id: int) -> None:
        """Clear user's dialog history."""
        key = f"{self.DIALOG_PREFIX}{user_id}"
        await self.redis.delete(key)

    async def get_dialog_length(self, user_id: int) -> int:
        """Get number of messages in dialog."""
        key = f"{self.DIALOG_PREFIX}{user_id}"
        return await self.redis.llen(key)

    async def set_session_value(self, user_id: int, key: str, value: Any, ttl: int | None = None) -> None:
        """Set a session value for a user."""
        session_key = f"{self.SESSION_PREFIX}{user_id}:{key}"
        await self.redis.set(
            session_key,
            json.dumps(value),
            ex=ttl or self.SESSION_TTL,
        )

    async def get_session_value(self, user_id: int, key: str, default: Any = None) -> Any:
        """Get a session value for a user."""
        session_key = f"{self.SESSION_PREFIX}{user_id}:{key}"
        value = await self.redis.get(session_key)
        if value:
            return json.loads(value)
        return default

    async def delete_session_value(self, user_id: int, key: str) -> None:
        """Delete a session value."""
        session_key = f"{self.SESSION_PREFIX}{user_id}:{key}"
        await self.redis.delete(session_key)

    async def increment_rate_limit(self, user_id: int, window: str = "minute") -> int:
        """Increment rate limit counter and return current count."""
        key = f"{self.RATE_LIMIT_PREFIX}{user_id}:{window}"
        pipe = self.redis.pipeline()

        if window == "minute":
            pipe.incr(key)
            pipe.expire(key, 60)
        elif window == "hour":
            pipe.incr(key)
            pipe.expire(key, 3600)
        else:
            pipe.incr(key)
            pipe.expire(key, self.DEFAULT_TTL)

        results = await pipe.execute()
        return results[0]

    async def get_rate_limit_count(self, user_id: int, window: str = "minute") -> int:
        """Get current rate limit count."""
        key = f"{self.RATE_LIMIT_PREFIX}{user_id}:{window}"
        value = await self.redis.get(key)
        return int(value) if value else 0

    async def is_rate_limited(self, user_id: int) -> bool:
        """Check if user is rate limited."""
        minute_count = await self.get_rate_limit_count(user_id, "minute")
        if minute_count >= settings.rate_limit.rate_limit_messages_per_minute:
            return True

        hour_count = await self.get_rate_limit_count(user_id, "hour")
        if hour_count >= settings.rate_limit.rate_limit_messages_per_hour:
            return True

        return False

    async def set_task_status(
        self,
        task_id: str,
        status: str,
        progress: int = 0,
        ttl: int = 86400,
    ) -> None:
        """Set status for a background task."""
        key = f"{self.TASK_PREFIX}{task_id}"
        await self.redis.set(
            key,
            json.dumps({"status": status, "progress": progress}),
            ex=ttl,
        )

    async def get_task_status(self, task_id: str) -> dict[str, Any] | None:
        """Get status of a background task."""
        key = f"{self.TASK_PREFIX}{task_id}"
        value = await self.redis.get(key)
        if value:
            return json.loads(value)
        return None

    async def update_task_progress(
        self,
        task_id: str,
        progress: int,
        status: str | None = None,
    ) -> None:
        """Update progress for a background task."""
        current = await self.get_task_status(task_id)
        if current:
            current["progress"] = progress
            if status:
                current["status"] = status
            key = f"{self.TASK_PREFIX}{task_id}"
            await self.redis.set(key, json.dumps(current))


_redis_client: redis.Redis | None = None


async def get_redis_client() -> redis.Redis:
    """Get or create Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.redis.redis_url,
            encoding="utf-8",
            decode_responses=False,
        )
    return _redis_client


async def close_redis() -> None:
    """Close Redis connection."""
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None


def get_short_term_memory(redis_client: redis.Redis) -> ShortTermMemory:
    """Create ShortTermMemory instance."""
    return ShortTermMemory(redis_client)