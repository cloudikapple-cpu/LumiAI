"""API module - FastAPI server and routes."""

from app.api.server import create_app, get_app
from app.api.routes import health, admin, metrics

__all__ = [
    "create_app",
    "get_app",
    "health",
    "admin",
    "metrics",
]