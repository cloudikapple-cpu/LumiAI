"""Photo handler for Telegram bot."""

from aiogram import Router, F
from aiogram.types import Message, PhotoSize

from app.services.multimodal import get_multimodal_service
from app.db.repositories.user_repo import UserRepository
from app.db.base import acquire_session


router = Router(name="photo")


@router.message(F.photo)
async def handle_photo(message: Message) -> None:
    """Handle photo messages."""
    user_id = message.from_user.id

    photo: PhotoSize | None = message.photo[-1]
    if not photo:
        await message.answer("Failed to process the image.")
        return

    thinking_msg = None
    try:
        thinking_msg = await message.answer("🖼️ Analyzing image...")

        file = await message.bot.get_file(photo.file_id)
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

        result = await multimodal.process_photo(
            user_id=user_id,
            file_path=file_path,
            caption=message.caption,
            prompt=None,
        )

        if thinking_msg:
            await thinking_msg.delete()

        if result.get("success"):
            response = result["response"]
        else:
            response = result.get("response", "I encountered an error analyzing the image.")

        await message.answer(response)

    except Exception as e:
        if thinking_msg:
            try:
                await thinking_msg.edit_text("⚠️ An error occurred while analyzing the image.")
            except Exception:
                pass