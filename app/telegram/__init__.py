"""Telegram bot module."""

from app.telegram.bot import create_bot, get_dispatcher
from app.telegram.handlers import (
    text,
    photo,
    voice,
    video,
    document,
    commands,
    errors,
)

__all__ = [
    "create_bot",
    "get_dispatcher",
    "text",
    "photo",
    "voice",
    "video",
    "document",
    "commands",
    "errors",
]