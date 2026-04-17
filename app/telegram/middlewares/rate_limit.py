"""Rate limiting middleware for Telegram bot."""

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from app.config import settings
from app.memory.short_term import get_redis_client, get_short_term_memory
from core.exceptions import RateLimitError


class RateLimitMiddleware(BaseMiddleware):
    """
    Middleware for rate limiting user messages.

    Limits:
    - Per minute: configurable (default 60)
    - Per hour: configurable (default 1000)
    """

    async def __call__(
        self,
        handler,
        event: TelegramObject,
        data: dict,
    ) -> any:
        if not isinstance(event, Message):
            return await handler(event, data)

        user_id = event.from_user.id

        redis_client = await get_redis_client()
        short_term = get_short_term_memory(redis_client)

        is_limited = await short_term.is_rate_limited(user_id)

        if is_limited:
            await event.answer(
                "⚠️ You've sent too many messages. Please wait a moment before sending more."
            )
            raise RateLimitError(f"User {user_id} hit rate limit")

        await short_term.increment_rate_limit(user_id, "minute")
        await short_term.increment_rate_limit(user_id, "hour")

        return await handler(event, data)