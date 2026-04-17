"""Command handlers for Telegram bot."""

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command, CommandStart, CommandHelp, CommandSettings, CommandReset

from app.services.user_settings import AVAILABLE_MODES, AVAILABLE_STYLES
from app.db.repositories.user_repo import UserRepository
from app.db.repositories.memory_repo import MemoryRepository
from app.db.base import acquire_session


router = Router(name="commands")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Handle /start command."""
    welcome_text = (
        "Welcome to LumiAI! I'm your AI assistant with advanced capabilities.\n\n"
        "I can help you with:\n"
        "• Text conversations with memory\n"
        "• Image analysis and OCR\n"
        "• Voice message transcription\n"
        "• Document understanding\n"
        "• Web search for current info\n"
        "• And much more!\n\n"
        "Type /help to see available commands."
    )
    await message.answer(welcome_text)


@router.message(CommandHelp())
async def cmd_help(message: Message) -> None:
    """Handle /help command."""
    help_text = (
        "📚 Available Commands:\n\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/settings - Configure bot settings\n"
        "/reset - Clear conversation context\n"
        "/memory - View your stored memory\n"
        "/forget - Clear all memory\n"
        "/forget_last - Clear last conversation\n"
        "/mode - Change assistant mode\n"
        "/about - About LumiAI\n\n"
        "💡 Tips:\n"
        "• Send photos for analysis\n"
        "• Send voice messages for transcription\n"
        "• Send documents for Q&A\n"
        "• Mention specific questions about images or documents"
    )
    await message.answer(help_text)


@router.message(CommandSettings())
async def cmd_settings(message: Message) -> None:
    """Handle /settings command."""
    keyboard_text = (
        "⚙️ Settings:\n\n"
        "Configure your experience with these options:\n\n"
        "• /mode - Change between Assistant, Explorer, or Concise modes\n"
        "• /reset - Clear current conversation context\n"
        "• /memory - View your stored preferences\n\n"
        "Currently supported modes:\n"
        f"• {', '.join(AVAILABLE_MODES)}\n\n"
        "Currently supported styles:\n"
        f"• {', '.join(AVAILABLE_STYLES)}"
    )
    await message.answer(keyboard_text)


@router.message(CommandReset())
async def cmd_reset(message: Message) -> None:
    """Handle /reset command - clear conversation context."""
    from app.services.chat import get_chat_service
    from app.memory.short_term import get_short_term_memory, get_redis_client

    redis_client = await get_redis_client()
    short_term = get_short_term_memory(redis_client)
    chat_service = get_chat_service(short_term_memory=short_term)

    await chat_service.clear_context(message.from_user.id)

    await message.answer("🔄 Conversation context has been cleared.")


@router.message(Command("memory"))
async def cmd_memory(message: Message) -> None:
    """Handle /memory command - show user's memory summary."""
    async with acquire_session() as session:
        user_repo = UserRepository(session)
        memory_repo = MemoryRepository(session)

        user = await user_repo.get_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("I don't have any memory stored for you yet.")
            return

        summary = await memory_repo.get_memory_summary(user.id)

        if summary["total"] == 0:
            await message.answer(
                "📝 Your memory is empty.\n\n"
                "I store important facts about you to provide personalized assistance. "
                "Just tell me things you'd like me to remember!"
            )
            return

        categories_text = "\n".join(
            f"  • {cat}: {count}" for cat, count in summary["by_category"].items()
        )

        response = (
            "📝 Your Memory Summary:\n\n"
            f"Total memories: {summary['total']}\n"
            f"High importance: {summary['high_importance']}\n\n"
            "By category:\n"
            f"{categories_text}\n\n"
            "Use /forget to clear all memory."
        )

        await message.answer(response)


@router.message(Command("forget"))
async def cmd_forget(message: Message) -> None:
    """Handle /forget command - delete all user memory."""
    async with acquire_session() as session:
        user_repo = UserRepository(session)
        memory_repo = MemoryRepository(session)

        user = await user_repo.get_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("I don't have any memory to forget.")
            return

        deleted = await memory_repo.delete_all_memories(user.id)

        await message.answer(f"🗑️ Forgotten {deleted} memories. Your memory is now clear.")


@router.message(Command("forget_last"))
async def cmd_forget_last(message: Message) -> None:
    """Handle /forget_last command - delete last conversation summary."""
    async with acquire_session() as session:
        user_repo = UserRepository(session)
        memory_repo = MemoryRepository(session)

        user = await user_repo.get_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("No recent conversation to forget.")
            return

        await memory_repo.forget_last_dialog(user.id)

        await message.answer("🗑️ Last conversation has been removed from memory.")


@router.message(Command("mode"))
async def cmd_mode(message: Message) -> None:
    """Handle /mode command - change assistant mode."""
    from core.types import UserMode

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        async with acquire_session() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_telegram_id(message.from_user.id)
            if user:
                try:
                    current_mode = UserMode(user.mode)
                except ValueError:
                    current_mode = UserMode.ASSISTANT
            else:
                current_mode = UserMode.ASSISTANT

        await message.answer(
            f"Current mode: {current_mode.value}\n\n"
            "Available modes:\n"
            "• assistant - Balanced responses\n"
            "• explorer - Deep research, more details\n"
            "• concise - Brief, to-the-point answers\n\n"
            "Use /mode <name> to change (e.g., /mode explorer)"
        )
        return

    mode_name = parts[1].strip().lower()
    try:
        new_mode = UserMode(mode_name)
    except ValueError:
        await message.answer(f"Unknown mode: {mode_name}\nValid modes: {', '.join(AVAILABLE_MODES)}")
        return

    async with acquire_session() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_or_create(telegram_id=message.from_user.id)
        await user_repo.update_mode(user.id, new_mode)

    await message.answer(f"✅ Mode changed to: {new_mode.value}")


@router.message(Command("about"))
async def cmd_about(message: Message) -> None:
    """Handle /about command."""
    about_text = (
        "ℹ️ About LumiAI\n\n"
        "Version: 1.0.0\n"
        "Framework: aiogram 3.x + FastAPI\n\n"
        "Features:\n"
        "• Multi-provider LLM support (OpenRouter, NVIDIA NIM, Groq)\n"
        "• Vision, audio, and document analysis\n"
        "• Web search integration\n"
        "• User memory and preferences\n"
        "• Streaming responses\n"
        "• Background task processing\n\n"
        "Your data is processed securely and not shared with third parties."
    )
    await message.answer(about_text)