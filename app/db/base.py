"""Database base configuration and session management."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import settings

engine: AsyncEngine | None = None
session_manager: async_sessionmaker[AsyncSession] | None = None


def init_db() -> None:
    """Initialize database engine and session maker."""
    global engine, session_manager

    engine = create_async_engine(
        settings.db.database_url,
        pool_size=settings.db.database_pool_size,
        max_overflow=settings.db.database_max_overflow,
        echo=settings.debug if hasattr(settings, "debug") else False,
        pool_pre_ping=True,
    )

    session_manager = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


async def close_db() -> None:
    """Close database connections."""
    global engine
    if engine:
        await engine.dispose()
        engine = None


async def get_session() -> AsyncIterator[AsyncSession]:
    """
    Dependency for getting async database session.

    Usage:
        async with get_session() as session:
            ...
    """
    if session_manager is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with session_manager() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def acquire_session() -> AsyncIterator[AsyncSession]:
    """
    Context manager for acquiring a session outside of dependency injection.

    Usage:
        async with acquire_session() as session:
            ...
    """
    if session_manager is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with session_manager() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_tables() -> None:
    """Create all tables. Use Alembic for production migrations."""
    from app.db.models import Base

    if engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)