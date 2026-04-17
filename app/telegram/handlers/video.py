"""Video handler for Telegram bot."""

from aiogram import Router, F
from aiogram.types import Message, Video

from app.services.multimodal import get_multimodal_service
from app.db.repositories.user_repo import UserRepository
from app.db.base import acquire_session


router = Router(name="video")


@router.message(F.video)
async def handle_video(message: Message) -> None:
    """Handle video messages."""
    user_id = message.from_user.id

    video: Video | None = message.video
    if not video:
        await message.answer("Failed to process the video.")
        return

    processing_msg = None
    try:
        processing_msg = await message.answer(
            "🎬 Video received. Processing will take a few minutes...\n"
            "You'll be notified when it's ready."
        )

        file = await message.bot.get_file(video.file_id)
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

        result = await multimodal.process_video(
            user_id=user_id,
            file_path=file_path,
            prompt=message.caption,
        )

        if result.get("status") == "queued":
            await processing_msg.edit_text(
                "✅ Video queued for processing.\n"
                "This may take a few minutes. Thank you for your patience!"
            )
        else:
            if processing_msg:
                await processing_msg.delete()
            await message.answer(result.get("response", "Video processed."))

    except Exception as e:
        if processing_msg:
            try:
                await processing_msg.edit_text("⚠️ An error occurred while processing the video.")
            except Exception:
                pass