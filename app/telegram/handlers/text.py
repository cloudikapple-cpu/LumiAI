"""Text message handler for Telegram bot."""

import asyncio

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from app.services.chat import get_chat_service
from app.services.user_settings import UserSettingsService
from app.memory.short_term import get_short_term_memory, get_redis_client
from app.db.repositories.user_repo import UserRepository
from app.db.base import acquire_session
from core.types import MessageType, UserMode


router = Router(name="text")


@router.message(F.text & ~Command())
async def handle_text(message: Message) -> None:
    """Handle regular text messages."""
    user_id = message.from_user.id
    text = message.text.strip()

    if not text:
        return

    thinking_msg = None
    try:
        thinking_msg = await message.answer("🤔 Thinking...")

        async with acquire_session() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_or_create(
                telegram_id=user_id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
            )
            await user_repo.update_last_seen(user.id)

            settings_service = UserSettingsService(session)
            settings = await settings_service.get_settings(user.id)
            user_mode_str = await settings_service.get_mode(user.id)
            try:
                user_mode = UserMode(user_mode_str)
            except ValueError:
                user_mode = UserMode.ASSISTANT

        redis_client = await get_redis_client()
        short_term = get_short_term_memory(redis_client)
        chat_service = get_chat_service(short_term_memory=short_term)

        streaming = settings.get("streaming_enabled", True)

        if streaming:
            full_response = []
            chunks = []

            try:
                async for chunk in chat_service.process_message_stream(
                    user_id=user_id,
                    message=text,
                    user_mode=user_mode,
                ):
                    chunks.append(chunk)

                    if len(chunks) >= 3:
                        partial = "".join(chunks)
                        if len(partial) > 100:
                            try:
                                await thinking_msg.edit_text(partial[:4096] + "█")
                            except Exception:
                                pass
                        full_response = chunks
                        chunks = []

                final_response = "".join(chunks) if chunks else "".join(full_response[-1000:]) if full_response else ""

            except Exception as streaming_error:
                result = await chat_service.process_message(
                    user_id=user_id,
                    message=text,
                    message_type=MessageType.TEXT,
                    user_mode=user_mode,
                    streaming=False,
                )
                final_response = result.get("response", "I encountered an error. Please try again.")

        else:
            result = await chat_service.process_message(
                user_id=user_id,
                message=text,
                message_type=MessageType.TEXT,
                user_mode=user_mode,
                streaming=False,
            )
            final_response = result.get("response", "I encountered an error. Please try again.")

        if thinking_msg:
            try:
                await thinking_msg.delete()
            except Exception:
                pass

        await send_long_message(message, final_response)

    except Exception as e:
        if thinking_msg:
            try:
                await thinking_msg.edit_text("⚠️ An error occurred. Please try again.")
            except Exception:
                pass


async def send_long_message(message: Message, text: str, max_length: int = 4096) -> None:
    """Send a potentially long message, splitting if necessary."""
    if len(text) <= max_length:
        await message.answer(text)
        return

    parts = split_text(text, max_length)

    for i, part in enumerate(parts):
        if i == 0:
            await message.answer(part)
        else:
            await message.answer(f"[{i + 1}/{len(parts)}]\n{part}")

        if i < len(parts) - 1:
            await asyncio.sleep(0.5)


def split_text(text: str, max_length: int) -> list[str]:
    """Split text into parts that fit within max_length."""
    parts = []

    lines = text.split("\n")
    current_part = ""

    for line in lines:
        if len(current_part) + len(line) + 1 <= max_length:
            current_part += line + "\n"
        else:
            if current_part:
                parts.append(current_part.strip())

            if len(line) <= max_length:
                current_part = line + "\n"
            else:
                words = line.split(" ")
                current_part = ""
                for word in words:
                    if len(current_part) + len(word) + 1 <= max_length:
                        current_part += word + " "
                    else:
                        if current_part:
                            parts.append(current_part.strip())
                        current_part = word + " "
                current_part += "\n"

    if current_part.strip():
        parts.append(current_part.strip())

    return parts