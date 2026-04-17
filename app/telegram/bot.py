"""Telegram bot setup and dispatcher configuration."""

import asyncio
from typing import Any

import httpx
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, ExceptionTypeFilter
from aiogram.types import Update
from aiogram.utils.token import TokenValidator

from app.config import settings


def create_bot() -> tuple[Bot, Dispatcher]:
    """
    Create and configure the Telegram bot and dispatcher.

    Returns:
        Tuple of (Bot, Dispatcher) instances
    """
    if not settings.telegram.bot_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set")

    token_validator = TokenValidator(settings.telegram.bot_token)
    token_validator.validate()

    bot = Bot(
        token=settings.telegram.bot_token,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
            link_preview_is_disabled=True,
        ),
        http_client=httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        ),
    )

    dp = Dispatcher(
        worker_buffer_size=32,
        events_isolation=asyncio.Lock(),
    )

    _register_routes(dp)

    return bot, dp


def _register_routes(dp: Dispatcher) -> None:
    """Register all routes with the dispatcher."""
    from app.telegram.handlers import commands, text, photo, voice, video, document, errors
    from app.telegram.middlewares import rate_limit, session, anti_spam

    dp.message.middleware(rate_limit.RateLimitMiddleware())
    dp.message.middleware(session.SessionMiddleware())
    dp.message.middleware(anti_spam.AntiSpamMiddleware())

    dp.include_routers(
        commands.router,
        text.router,
        photo.router,
        voice.router,
        video.router,
        document.router,
        errors.router,
    )


async def set_webhook(bot: Bot) -> None:
    """Configure webhook for the bot."""
    if settings.telegram.webhook_domain:
        await bot.set_webhook(
            url=f"{settings.telegram.webhook_domain}{settings.telegram.webhook_path}",
            allowed_updates=Update.model_fields.keys(),
        )


async def delete_webhook(bot: Bot) -> None:
    """Remove webhook configuration."""
    await bot.delete_webhook(drop_pending_updates=True)


async def start_bot(bot: Bot, dp: Dispatcher) -> None:
    """Start the bot using polling or webhook based on configuration."""
    if settings.telegram.webhook_domain:
        await set_webhook(bot)
        await dp.start_webhook(
            listen="0.0.0.0",
            port=8443,
            webhook_path=settings.telegram.webhook_path,
        )
    else:
        await delete_webhook(bot)
        await dp.start_polling(bot, allowed_updates=Update.model_fields.keys())


_dispatcher: Dispatcher | None = None


def get_dispatcher() -> Dispatcher:
    """Get the configured dispatcher."""
    global _dispatcher
    if _dispatcher is None:
        _, _dispatcher = create_bot()
    return _dispatcher