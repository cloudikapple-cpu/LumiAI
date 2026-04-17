"""Dialog repository for conversation history operations."""

from datetime import datetime

from sqlalchemy import select, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Dialog, DialogMessage


class DialogRepository:
    """Repository for dialog/conversation operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_dialog(self, user_id: int, title: str | None = None) -> Dialog:
        """Create a new dialog."""
        dialog = Dialog(user_id=user_id, title=title)
        self.session.add(dialog)
        await self.session.flush()
        return dialog

    async def get_dialog(self, dialog_id: int) -> Dialog | None:
        """Get dialog by ID."""
        result = await self.session.execute(
            select(Dialog).where(Dialog.id == dialog_id)
        )
        return result.scalar_one_or_none()

    async def get_user_dialogs(
        self, user_id: int, include_archived: bool = False, limit: int = 50
    ) -> list[Dialog]:
        """Get all dialogs for a user."""
        query = select(Dialog).where(Dialog.user_id == user_id)
        if not include_archived:
            query = query.where(Dialog.is_archived == False)
        query = query.where(Dialog.is_deleted == False)
        query = query.order_by(Dialog.last_message_at.desc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def add_message(
        self,
        dialog_id: int,
        role: str,
        content: str,
        media_type: str | None = None,
        media_url: str | None = None,
        media_caption: str | None = None,
        model: str | None = None,
        provider: str | None = None,
        tokens_used: int | None = None,
    ) -> DialogMessage:
        """Add a message to a dialog."""
        message = DialogMessage(
            dialog_id=dialog_id,
            role=role,
            content=content,
            media_type=media_type,
            media_url=media_url,
            media_caption=media_caption,
            model=model,
            provider=provider,
            tokens_used=tokens_used,
        )
        self.session.add(message)

        await self.session.execute(
            select(Dialog)
            .where(Dialog.id == dialog_id)
            .update({Dialog.last_message_at: datetime.utcnow()})
        )

        await self.session.flush()
        return message

    async def get_dialog_messages(
        self, dialog_id: int, limit: int = 100, offset: int = 0
    ) -> list[DialogMessage]:
        """Get messages from a dialog."""
        result = await self.session.execute(
            select(DialogMessage)
            .where(DialogMessage.dialog_id == dialog_id)
            .order_by(DialogMessage.created_at)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_recent_messages(self, user_id: int, limit: int = 50) -> list[DialogMessage]:
        """Get recent messages across all user's dialogs."""
        result = await self.session.execute(
            select(DialogMessage)
            .join(Dialog)
            .where(
                and_(
                    Dialog.user_id == user_id,
                    Dialog.is_deleted == False,
                )
            )
            .order_by(DialogMessage.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete_dialog(self, dialog_id: int) -> bool:
        """Soft delete a dialog."""
        result = await self.session.execute(
            select(Dialog)
            .where(Dialog.id == dialog_id)
            .update({Dialog.is_deleted: True})
        )
        await self.session.flush()
        return result.rowcount > 0

    async def archive_dialog(self, dialog_id: int) -> bool:
        """Archive a dialog."""
        result = await self.session.execute(
            select(Dialog)
            .where(Dialog.id == dialog_id)
            .update({Dialog.is_archived: True})
        )
        await self.session.flush()
        return result.rowcount > 0

    async def get_dialog_stats(self, user_id: int) -> dict:
        """Get statistics about user's dialogs."""
        result = await self.session.execute(
            select(
                func.count(Dialog.id).label("total_dialogs"),
                func.sum(func.length(DialogMessage.content)).label("total_chars"),
            )
            .select_from(Dialog)
            .join(DialogMessage)
            .where(
                and_(
                    Dialog.user_id == user_id,
                    Dialog.is_deleted == False,
                )
            )
        )
        row = result.one()
        return {
            "total_dialogs": row.total_dialogs or 0,
            "total_characters": row.total_chars or 0,
        }

    async def compress_dialog(self, dialog_id: int, keep_last_n: int = 10) -> int:
        """
        Compress a dialog by keeping only the last N messages.
        Returns the number of messages deleted.
        """
        result = await self.session.execute(
            select(DialogMessage)
            .where(DialogMessage.dialog_id == dialog_id)
            .order_by(DialogMessage.created_at.desc())
            .limit(keep_last_n)
        )
        kept_messages = list(result.scalars().all())
        kept_ids = [m.id for m in kept_messages]

        if not kept_ids:
            return 0

        delete_count = 0
        for msg in kept_messages:
            if msg.tokens_used:
                delete_count += 1

        await self.session.execute(
            delete(DialogMessage).where(
                and_(
                    DialogMessage.dialog_id == dialog_id,
                    DialogMessage.id.notin_(kept_ids),
                )
            )
        )
        await self.session.flush()
        return delete_count