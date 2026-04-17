"""Error handler for Telegram bot."""

from aiogram import Router, F
from aiogram.types import Message, Update

from core.exceptions import RateLimitError, AntiSpamError


router = Router(name="errors")


@router.errors()
async def handle_error(event: Update, exception: Exception) -> None:
    """Handle exceptions in the dispatcher."""
    from app.logging import get_logger

    logger = get_logger("telegram.errors")

    if isinstance(exception, RateLimitError):
        logger.warning(f"Rate limit hit: {exception.message}")
        return

    if isinstance(exception, AntiSpamError):
        logger.warning(f"Anti-spam triggered: {exception.message}")
        return

    logger.error(
        f"Unhandled exception in Telegram handler: {exception}",
        exc_info=exception,
    )


@router.update()
async def handle_update_error(update: Update, exception: Exception) -> None:
    """Handle exceptions in update processing."""
    from app.logging import get_logger

    logger = get_logger("telegram.update_errors")

    logger.error(
        f"Update processing error: {exception}",
        exc_info=exception,
    )