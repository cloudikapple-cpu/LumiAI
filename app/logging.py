"""Logging configuration using Loguru."""

import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from loguru import logger

from app.config import settings


def setup_logging() -> None:
    """Configure Loguru logging based on settings."""

    logger.remove()

    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    if settings.debug:
        log_level = "DEBUG"
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
    else:
        log_level = settings.log_level

    logger.add(
        sys.stderr,
        format=log_format,
        level=log_level,
        backtrace=True,
        diagnose=settings.debug,
    )

    logs_dir = Path("logs")
    if logs_dir.exists() or settings.debug:
        if not logs_dir.exists():
            logs_dir.mkdir(parents=True, exist_ok=True)

        logger.add(
            logs_dir / "lumi-ai-{time:YYYY-MM-DD}.log",
            rotation="00:00",
            retention="7 days",
            compression="zip",
            format=log_format,
            level="DEBUG" if settings.debug else "INFO",
            backtrace=True,
            diagnose=settings.debug,
        )


@contextmanager
def log_context(**kwargs):
    """Add contextual information to log records."""
    token = logger.bind(**kwargs). contextualize()
    try:
        yield
    finally:
        token.__exit__(None, None, None)


def get_logger(name: str):
    """Get a logger instance with the given name."""
    return logger.bind(name=name)