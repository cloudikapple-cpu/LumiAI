"""SQLAlchemy ORM models."""

from datetime import datetime
from typing import Any
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    BigInteger,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from core.types import UserMode


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    type_annotation_map = {
        str: Text,
        dict: JSON,
        bool: Boolean,
        int: BigInteger,
    }


class User(Base):
    """User model - stores user information and preferences."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language_code: Mapped[str] = mapped_column(String(10), default="en")
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    mode: Mapped[str] = mapped_column(String(20), default=UserMode.ASSISTANT.value)
    assistant_style: Mapped[str] = mapped_column(String(50), default="balanced")
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    settings: Mapped["UserSettings"] = relationship(
        "UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    memories: Mapped[list["UserMemory"]] = relationship(
        "UserMemory", back_populates="user", cascade="all, delete-orphan"
    )
    dialogs: Mapped[list["Dialog"]] = relationship(
        "Dialog", back_populates="user", cascade="all, delete-orphan"
    )


class UserSettings(Base):
    """User-specific settings."""

    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )

    web_search_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    memory_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_compress_context: Mapped[bool] = mapped_column(Boolean, default=True)

    max_context_messages: Mapped[int] = mapped_column(Integer, default=50)
    streaming_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    default_temperature: Mapped[float] = mapped_column(default=0.7)
    default_max_tokens: Mapped[int] = mapped_column(Integer, default=4096)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship("User", back_populates="settings")


class UserMemory(Base):
    """Long-term user memory."""

    __tablename__ = "user_memories"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    category: Mapped[str] = mapped_column(String(50), index=True)
    key: Mapped[str] = mapped_column(String(255), index=True)
    value: Mapped[str] = mapped_column(Text)
    importance: Mapped[int] = mapped_column(Integer, default=1)

    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship("User", back_populates="memories")

    __table_args__ = (
        Index("ix_user_memory_user_category", "user_id", "category"),
        Index("ix_user_memory_user_key", "user_id", "key"),
    )


class Dialog(Base):
    """Dialog/conversation model."""

    __tablename__ = "dialogs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_message_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="dialogs")
    messages: Mapped[list["DialogMessage"]] = relationship(
        "DialogMessage",
        back_populates="dialog",
        cascade="all, delete-orphan",
        order_by="DialogMessage.created_at",
    )

    __table_args__ = (
        Index("ix_dialog_user_updated", "user_id", "updated_at"),
    )


class DialogMessage(Base):
    """Individual message in a dialog."""

    __tablename__ = "dialog_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    dialog_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dialogs.id", ondelete="CASCADE"), index=True
    )

    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)

    media_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    media_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    media_caption: Mapped[str | None] = mapped_column(Text, nullable=True)

    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)

    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    dialog: Mapped["Dialog"] = relationship("Dialog", back_populates="messages")

    __table_args__ = (
        Index("ix_dialog_message_dialog_created", "dialog_id", "created_at"),
    )


class Task(Base):
    """Background task tracking."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    task_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)

    task_type: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)

    input_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    progress: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=100)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_task_user_status", "user_id", "status"),
    )