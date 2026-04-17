"""Inline keyboards for Telegram bot."""

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup


def create_mode_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard for mode selection."""
    builder = InlineKeyboardBuilder()

    builder.button(text="🤖 Assistant", callback_data="mode:assistant")
    builder.button(text="🔍 Explorer", callback_data="mode:explorer")
    builder.button(text="⚡ Concise", callback_data="mode:concise")

    builder.adjust(3)

    return builder.as_markup()


def create_settings_keyboard() -> InlineKeyboardMarkup:
    """Create keyboard for settings."""
    builder = InlineKeyboardBuilder()

    builder.button(text="🔄 Toggle Web Search", callback_data="settings:web_search")
    builder.button(text="🧠 Toggle Memory", callback_data="settings:memory")
    builder.button(text="📝 Set Style", callback_data="settings:style")
    builder.button(text="🔙 Back", callback_data="settings:back")

    builder.adjust(2)

    return builder.as_markup()