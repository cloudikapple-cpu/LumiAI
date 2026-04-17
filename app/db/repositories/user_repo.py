"""User repository for database operations."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, UserSettings
from core.types import UserMode


class UserRepository:
    """Repository for user-related database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Get user by Telegram ID."""
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, telegram_id: int, **defaults) -> User:
        """Get existing user or create new one."""
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            return user

        user = User(telegram_id=telegram_id, **defaults)
        self.session.add(user)
        await self.session.flush()

        settings = UserSettings(user_id=user.id)
        self.session.add(settings)

        await self.session.flush()
        return user

    async def update_last_seen(self, user_id: int) -> None:
        """Update user's last seen timestamp."""
        await self.session.execute(
            select(User)
            .where(User.id == user_id)
            .update({User.last_seen_at: datetime.utcnow()})
        )

    async def update_mode(self, user_id: int, mode: UserMode) -> None:
        """Update user's assistant mode."""
        await self.session.execute(
            select(User)
            .where(User.id == user_id)
            .update({User.mode: mode.value})
        )

    async def update_settings(self, user_id: int, **settings) -> None:
        """Update user settings."""
        result = await self.session.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        user_settings = result.scalar_one_or_none()
        if user_settings:
            for key, value in settings.items():
                if hasattr(user_settings, key):
                    setattr(user_settings, key, value)
        await self.session.flush()

    async def block_user(self, user_id: int) -> None:
        """Block a user."""
        await self.session.execute(
            select(User)
            .where(User.id == user_id)
            .update({User.is_blocked: True})
        )

    async def unblock_user(self, user_id: int) -> None:
        """Unblock a user."""
        await self.session.execute(
            select(User)
            .where(User.id == user_id)
            .update({User.is_blocked: False})
        )

    async def is_admin(self, user_id: int) -> bool:
        """Check if user is admin."""
        result = await self.session.execute(
            select(User.is_admin).where(User.id == user_id)
        )
        return result.scalar_one_or_none() or False