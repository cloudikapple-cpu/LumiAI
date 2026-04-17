"""Anti-spam middleware for Telegram bot."""

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from core.exceptions import AntiSpamError


class AntiSpamMiddleware(BaseMiddleware):
    """
    Basic anti-spam middleware.

    Detects potential spam patterns:
    - Excessive caps
    - Repeated characters
    - Known spam keywords
    - Very short messages with links
    """

    SPAM_KEYWORDS = [
        "buy now",
        "click here",
        "free money",
        "make money fast",
        "act now",
        "limited time",
    ]

    MAX_CAPS_RATIO = 0.7
    MAX_REPEATED_CHARS = 5

    async def __call__(
        self,
        handler,
        event: TelegramObject,
        data: dict,
    ) -> any:
        if not isinstance(event, Message) or not event.text:
            return await handler(event, data)

        text = event.text

        if self._is_spam(text):
            await event.answer(
                "⚠️ Your message looks like spam. Please don't send spam messages."
            )
            raise AntiSpamError(f"Spam detected from user {event.from_user.id}")

        return await handler(event, data)

    def _is_spam(self, text: str) -> bool:
        """Check if message is spam."""
        text_lower = text.lower()

        for keyword in self.SPAM_KEYWORDS:
            if keyword in text_lower:
                return True

        if len(text) >= 10:
            caps_count = sum(1 for c in text if c.isupper())
            if caps_count / len(text) > self.MAX_CAPS_RATIO:
                return True

        for i in range(len(text) - self.MAX_REPEATED_CHARS):
            char = text[i]
            if all(text[i + j] == char for j in range(1, self.MAX_REPEATED_CHARS)):
                return True

        if len(text) < 20 and ("http://" in text_lower or "https://" in text_lower):
            return True

        return False