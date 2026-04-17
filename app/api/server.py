"""FastAPI server setup."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler."""
    await _init_services()
    yield
    await _cleanup_services()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="LumiAI API",
        description="Telegram AI Assistant Backend API",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    _register_routes(app)

    return app


def _register_routes(app: FastAPI) -> None:
    """Register all API routes."""
    from app.api.routes import health, admin, metrics

    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(admin.router, prefix="/api/v1", tags=["admin"])
    app.include_router(metrics.router, prefix="/api/v1", tags=["metrics"])


async def _init_services() -> None:
    """Initialize services on startup."""
    from app.db.base import init_db

    init_db()


async def _cleanup_services() -> None:
    """Cleanup services on shutdown."""
    from app.db.base import close_db
    from app.memory.short_term import close_redis

    await close_db()
    await close_redis()


_app: FastAPI | None = None


def get_app() -> FastAPI:
    """Get the FastAPI application instance."""
    global _app
    if _app is None:
        _app = create_app()
    return _app