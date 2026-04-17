"""Admin endpoints for bot management."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings


router = APIRouter()


class AdminStats(BaseModel):
    total_users: int
    total_dialogs: int
    total_memories: int
    providers: dict[str, Any]
    uptime_seconds: float


@router.get("/admin/stats")
async def get_stats() -> AdminStats:
    """
    Get bot statistics.

    Note: This endpoint should be protected in production.
    """
    from app.logging import get_logger

    logger = get_logger("admin")

    try:
        async with _get_db_session() as session:
            from sqlalchemy import select, func
            from app.db.models import User, Dialog, UserMemory

            user_count = await session.scalar(select(func.count(User.id)))
            dialog_count = await session.scalar(select(func.count(Dialog.id)))
            memory_count = await session.scalar(select(func.count(UserMemory.id)))

    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        user_count = 0
        dialog_count = 0
        memory_count = 0

    from app.llm.router import get_router

    llm_router = get_router()
    providers = {}
    for name, models in llm_router.list_providers():
        providers[name] = {
            "model_count": len(models),
            "capabilities": list(providers.values()),
        }

    return AdminStats(
        total_users=user_count or 0,
        total_dialogs=dialog_count or 0,
        total_memories=memory_count or 0,
        providers=providers,
        uptime_seconds=_get_uptime(),
    )


@router.post("/admin/cache/clear")
async def clear_cache() -> dict:
    """
    Clear all caches.

    Note: This endpoint should be protected in production.
    """
    from app.memory.short_term import get_redis_client

    try:
        redis_client = await get_redis_client()
        await redis_client.flushdb()
        return {"status": "success", "message": "Cache cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/users/{user_id}")
async def get_user(user_id: int) -> dict:
    """
    Get detailed user information.

    Note: This endpoint should be protected in production.
    """
    from app.db.repositories.user_repo import UserRepository
    from app.db.repositories.memory_repo import MemoryRepository
    from app.db.repositories.dialog_repo import DialogRepository
    from app.db.base import acquire_session

    async with acquire_session() as session:
        user_repo = UserRepository(session)
        memory_repo = MemoryRepository(session)
        dialog_repo = DialogRepository(session)

        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        from app.db.models import User
        from sqlalchemy import select

        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        memory_summary = await memory_repo.get_memory_summary(user_id)
        dialog_stats = await dialog_repo.get_dialog_stats(user_id)

        return {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "mode": user.mode,
            "created_at": user.created_at.isoformat(),
            "last_seen": user.last_seen_at.isoformat(),
            "memory": memory_summary,
            "dialogs": dialog_stats,
        }


import time

_start_time = time.time()


def _get_uptime() -> float:
    """Get application uptime in seconds."""
    return time.time() - _start_time


async def _get_db_session():
    """Get database session for stats."""
    from app.db.base import acquire_session
    return acquire_session()