"""Document handler for Telegram bot."""

from aiogram import Router, F
from aiogram.types import Message, Document

from app.services.multimodal import get_multimodal_service
from app.db.repositories.user_repo import UserRepository
from app.db.base import acquire_session


router = Router(name="document")


@router.message(F.document)
async def handle_document(message: Message) -> None:
    """Handle document messages."""
    user_id = message.from_user.id

    doc: Document | None = message.document
    if not doc:
        await message.answer("Failed to process the document.")
        return

    file_ext = doc.file_name.split(".")[-1].lower() if doc.file_name else ""

    supported_formats = ["pdf", "txt", "doc", "docx", "md", "rtf"]
    if file_ext not in supported_formats:
        await message.answer(
            f"Unsupported file format: .{file_ext}\n\n"
            f"Supported formats: {', '.join(supported_formats)}"
        )
        return

    processing_msg = None
    try:
        processing_msg = await message.answer(
            "📄 Document received. Processing...\n"
            "This may take a moment."
        )

        file = await message.bot.get_file(doc.file_id)
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

        result = await multimodal.process_document(
            user_id=user_id,
            file_path=file_path,
            prompt=message.caption,
        )

        if result.get("status") == "queued":
            await processing_msg.edit_text(
                "✅ Document queued for processing.\n"
                "You'll be notified when it's ready."
            )
        else:
            if processing_msg:
                await processing_msg.delete()
            await message.answer(result.get("response", "Document processed."))

    except Exception as e:
        if processing_msg:
            try:
                await processing_msg.edit_text("⚠️ An error occurred while processing the document.")
            except Exception:
                pass