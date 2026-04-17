"""Session middleware for Telegram bot."""

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject, Update

from app.db.repositories.user_repo import UserRepository
from app.db.base import acquire_session


class SessionMiddleware(BaseMiddleware):
    """
    Middleware for managing user sessions.

    Loads user data and attaches it to the event data.
    """

    async def __call__(
        self,
        handler,
        event: TelegramObject,
        data: dict,
    ) -> any:
        if isinstance(event, Update):
            message = event.message or event.edited_message
            if not message:
                return await handler(event, data)

            user_id = message.from_user.id

            async with acquire_session() as session:
                user_repo = UserRepository(session)
                user = await user_repo.get_or_create(
                    telegram_id=user_id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name,
                    last_name=message.from_user.last_name,
                )

                data["user"] = user
                data["user_repo"] = user_repo

        elif isinstance(event, Message):
            user_id = event.from_user.id

            async with acquire_session() as session:
                user_repo = UserRepository(session)
                user = await user_repo.get_or_create(
                    telegram_id=user_id,
                    username=event.from_user.username,
                    first_name=event.from_user.first_name,
                    last_name=event.from_user.last_name,
                )

                data["user"] = user
                data["user_repo"] = user_repo

        return await handler(event, data)