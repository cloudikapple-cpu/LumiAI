"""Voice message handler for Telegram bot."""

from aiogram import Router, F
from aiogram.types import Message, Audio

from app.services.multimodal import get_multimodal_service
from app.db.repositories.user_repo import UserRepository
from app.db.base import acquire_session


router = Router(name="voice")


@router.message(F.voice)
async def handle_voice(message: Message) -> None:
    """Handle voice messages."""
    user_id = message.from_user.id

    voice = message.voice
    if not voice:
        await message.answer("Failed to process the voice message.")
        return

    thinking_msg = None
    try:
        thinking_msg = await message.answer("🎤 Processing voice message...")

        file = await message.bot.get_file(voice.file_id)
        file_path = f"https://api.telegram.org/file/bot{message.bot.token}/{file.file_path}"

        async with acquire_session() as session:
            user_repo = UserRepository(session)
            await user_repo.get_or_create(
                telegram_id=user_id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
            )

        multimodal = get_multimodal_service()

        result = await multimodal.process_voice(
            user_id=user_id,
            file_path=file_path,
            prompt=None,
        )

        if thinking_msg:
            await thinking_msg.delete()

        if result.get("success"):
            response = result["response"]
        else:
            response = result.get("response", "I encountered an error processing the voice message.")

        await message.answer(response)

    except Exception as e:
        if thinking_msg:
            try:
                await thinking_msg.edit_text("⚠️ An error occurred while processing the voice message.")
            except Exception:
                pass