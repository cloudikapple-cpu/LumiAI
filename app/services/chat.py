"""Chat service - handles text conversations."""

from typing import Any, AsyncIterator

import redis.asyncio as redis

from core.interfaces import ChatMessage, ChatOptions
from core.types import LLMResponse, MessageType, UserMode
from app.llm.router import LLMRouter, get_router
from app.memory.short_term import ShortTermMemory, get_short_term_memory
from app.memory.long_term import LongTermMemory
from app.db.repositories.user_repo import UserRepository
from app.db.repositories.dialog_repo import DialogRepository
from app.db.base import acquire_session


class ChatService:
    """
    Service for handling text chat interactions.

    Responsibilities:
    - Manage conversation context
    - Handle streaming responses
    - Compress long contexts
    - Route to appropriate LLM
    - Store dialogue history
    """

    MAX_CONTEXT_MESSAGES = 50
    COMPRESS_THRESHOLD = 40

    def __init__(
        self,
        llm_router: LLMRouter | None = None,
        short_term_memory: ShortTermMemory | None = None,
    ):
        self.llm_router = llm_router or get_router()
        self.short_term_memory = short_term_memory

    async def process_message(
        self,
        user_id: int,
        message: str,
        message_type: MessageType = MessageType.TEXT,
        user_mode: UserMode = UserMode.ASSISTANT,
        system_prompt: str | None = None,
        streaming: bool = True,
    ) -> dict[str, Any]:
        """
        Process a user message and return a response.

        Args:
            user_id: User ID
            message: User message
            message_type: Type of message
            user_mode: User's assistant mode
            system_prompt: Custom system prompt
            streaming: Whether to stream the response

        Returns:
            Dictionary with response and metadata
        """
        async with acquire_session() as session:
            user_repo = UserRepository(session)
            dialog_repo = DialogRepository(session)

            user = await user_repo.get_or_create(telegram_id=user_id)

            dialog = await dialog_repo.create_dialog(user.id)

            history = await self.short_term_memory.get_dialog(user_id, limit=20) if self.short_term_memory else []

            await dialog_repo.add_message(
                dialog_id=dialog.id,
                role="user",
                content=message,
                media_type=message_type if message_type != MessageType.TEXT else None,
            )

            messages = await self._build_messages(
                message=message,
                history=history,
                system_prompt=system_prompt or user.system_prompt,
            )

            options = self._build_options(user_mode, streaming)

            try:
                response = await self.llm_router.chat_with_fallback(
                    messages=messages,
                    options=options,
                )

                await dialog_repo.add_message(
                    dialog_id=dialog.id,
                    role="assistant",
                    content=response["content"],
                    model=response.get("model"),
                    provider=response.get("provider"),
                    tokens_used=response.get("usage", {}).get("total_tokens"),
                )

                if self.short_term_memory:
                    await self.short_term_memory.add_dialog_message(
                        user_id=user_id,
                        role="user",
                        content=message,
                    )
                    await self.short_term_memory.add_dialog_message(
                        user_id=user_id,
                        role="assistant",
                        content=response["content"],
                    )

                return {
                    "response": response["content"],
                    "sources": response.get("sources", []),
                    "model": response.get("model"),
                    "provider": response.get("provider"),
                    "usage": response.get("usage", {}),
                }

            except Exception as e:
                return {
                    "error": str(e),
                    "response": "I apologize, but I encountered an error processing your message. Please try again.",
                }

    async def process_message_stream(
        self,
        user_id: int,
        message: str,
        user_mode: UserMode = UserMode.ASSISTANT,
    ) -> AsyncIterator[str]:
        """
        Process a message and yield chunks as they arrive (streaming).

        Args:
            user_id: User ID
            message: User message
            user_mode: User's assistant mode

        Yields:
            Text chunks as they arrive from the LLM
        """
        async with acquire_session() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_or_create(telegram_id=user_id)

        history = await self.short_term_memory.get_dialog(user_id, limit=20) if self.short_term_memory else []

        messages = await self._build_messages(
            message=message,
            history=history,
            system_prompt=user.system_prompt,
        )

        options = ChatOptions(
            temperature=0.7,
            max_tokens=4096,
            stream=True,
        )

        full_response = []
        async for chunk in self.llm_router.chat_stream(
            messages=messages,
            options=options,
        ):
            full_response.append(chunk)
            yield chunk

        if self.short_term_memory:
            await self.short_term_memory.add_dialog_message(
                user_id=user_id,
                role="user",
                content=message,
            )
            await self.short_term_memory.add_dialog_message(
                user_id=user_id,
                role="assistant",
                content="".join(full_response),
            )

    async def _build_messages(
        self,
        message: str,
        history: list[dict[str, Any]],
        system_prompt: str | None = None,
    ) -> list[ChatMessage]:
        """Build message list with system prompt and history."""
        messages = []

        if system_prompt:
            messages.append(ChatMessage(role="system", content=system_prompt))

        for msg in history[-self.MAX_CONTEXT_MESSAGES:]:
            messages.append(ChatMessage(
                role=msg.get("role", "user"),
                content=msg.get("content", ""),
            ))

        messages.append(ChatMessage(role="user", content=message))

        return messages

    def _build_options(
        self,
        user_mode: UserMode,
        streaming: bool,
    ) -> ChatOptions:
        """Build chat options based on user mode."""
        if user_mode == UserMode.CONCISE:
            return ChatOptions(
                temperature=0.5,
                max_tokens=1024,
                stream=streaming,
            )
        elif user_mode == UserMode.EXPLORER:
            return ChatOptions(
                temperature=0.8,
                max_tokens=8192,
                stream=streaming,
            )
        else:
            return ChatOptions(
                temperature=0.7,
                max_tokens=4096,
                stream=streaming,
            )

    async def compress_context(self, user_id: int) -> int:
        """
        Compress the conversation context for long dialogues.

        Returns:
            Number of messages removed
        """
        if not self.short_term_memory:
            return 0

        dialog_length = await self.short_term_memory.get_dialog_length(user_id)
        if dialog_length < self.COMPRESS_THRESHOLD:
            return 0

        current_dialog = await self.short_term_memory.get_dialog(user_id, limit=dialog_length)

        summary_prompt = (
            "Summarize this conversation briefly, preserving key facts and context. "
            "Format as: 'Conversation covered X topics: 1) ... 2) ...'"
        )

        messages = [
            ChatMessage(role="system", content=summary_prompt),
            *[ChatMessage(role=m.get("role", "user"), content=m.get("content", ""))
              for m in current_dialog[:30]],
        ]

        try:
            response = await self.llm_router.chat_with_fallback(
                messages=messages,
                options=ChatOptions(temperature=0.5, max_tokens=500),
            )

            summary = response["content"]

            await self.short_term_memory.clear_dialog(user_id)
            await self.short_term_memory.add_dialog_message(
                user_id=user_id,
                role="system",
                content=f"[Context summary] {summary}",
            )

            return dialog_length - 1

        except Exception:
            return 0

    async def clear_context(self, user_id: int) -> None:
        """Clear user's conversation context."""
        if self.short_term_memory:
            await self.short_term_memory.clear_dialog(user_id)


_chat_service: ChatService | None = None


def get_chat_service(
    llm_router: LLMRouter | None = None,
    short_term_memory: ShortTermMemory | None = None,
) -> ChatService:
    """Get or create the chat service."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService(llm_router, short_term_memory)
    return _chat_service