"""User settings service - manages user preferences."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, UserSettings
from app.db.repositories.user_repo import UserRepository
from core.types import UserMode


class UserSettingsService:
    """Service for managing user settings and preferences."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)

    async def get_settings(self, user_id: int) -> dict[str, Any]:
        """Get all settings for a user."""
        result = await self.session.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        settings = result.scalar_one_or_none()

        if not settings:
            return self._default_settings()

        return {
            "web_search_enabled": settings.web_search_enabled,
            "memory_enabled": settings.memory_enabled,
            "auto_compress_context": settings.auto_compress_context,
            "max_context_messages": settings.max_context_messages,
            "streaming_enabled": settings.streaming_enabled,
            "default_temperature": settings.default_temperature,
            "default_max_tokens": settings.default_max_tokens,
        }

    async def update_settings(self, user_id: int, **kwargs) -> dict[str, Any]:
        """Update specific settings for a user."""
        result = await self.session.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        settings = result.scalar_one_or_none()

        if not settings:
            settings = UserSettings(user_id=user_id)
            self.session.add(settings)

        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value)

        await self.session.flush()

        return await self.get_settings(user_id)

    async def get_mode(self, user_id: int) -> UserMode:
        """Get user's current assistant mode."""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            return UserMode.ASSISTANT

        try:
            return UserMode(user.mode)
        except ValueError:
            return UserMode.ASSISTANT

    async def set_mode(self, user_id: int, mode: UserMode) -> None:
        """Set user's assistant mode."""
        await self.session.execute(
            select(User)
            .where(User.id == user_id)
            .update({User.mode: mode.value})
        )
        await self.session.flush()

    async def get_assistant_style(self, user_id: int) -> str:
        """Get user's preferred assistant style."""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        return user.assistant_style if user and user.assistant_style else "balanced"

    async def set_assistant_style(self, user_id: int, style: str) -> None:
        """Set user's preferred assistant style."""
        valid_styles = ["concise", "balanced", "detailed", "creative", "technical"]
        if style not in valid_styles:
            raise ValueError(f"Invalid style. Must be one of: {valid_styles}")

        await self.session.execute(
            select(User)
            .where(User.id == user_id)
            .update({User.assistant_style: style})
        )
        await self.session.flush()

    def _default_settings(self) -> dict[str, Any]:
        """Return default settings."""
        return {
            "web_search_enabled": True,
            "memory_enabled": True,
            "auto_compress_context": True,
            "max_context_messages": 50,
            "streaming_enabled": True,
            "default_temperature": 0.7,
            "default_max_tokens": 4096,
        }


AVAILABLE_STYLES = ["concise", "balanced", "detailed", "creative", "technical"]
AVAILABLE_MODES = [mode.value for mode in UserMode]