"""Main entry point for the LumiAI bot application."""

import asyncio
import signal
from contextlib import asynccontextmanager
from typing import AsyncIterator

from app.logging import setup_logging, get_logger
from app.config import settings


@asynccontextmanager
async def lifespan() -> AsyncIterator[None]:
    """Application lifespan manager."""
    setup_logging()
    logger = get_logger("main")

    logger.info("Starting LumiAI Bot...")
    logger.info(f"Debug mode: {settings.debug}")

    await _init_async_services()

    logger.info("LumiAI Bot started successfully")

    yield

    logger.info("Shutting down LumiAI Bot...")
    await _cleanup_async_services()
    logger.info("LumiAI Bot stopped")


async def _init_async_services() -> None:
    """Initialize async services."""
    from app.db.base import init_db, init_tables
    from app.memory.short_term import get_redis_client
    from app.llm.router import get_router
    from app.tools.registry import get_registry

    init_db()
    await init_tables()

    await get_redis_client()

    get_router()

    get_registry()

    logger = get_logger("main")
    logger.info("Database and Redis connections initialized")
    logger.info("LLM router and tools initialized")


async def _cleanup_async_services() -> None:
    """Cleanup async services."""
    from app.db.base import close_db
    from app.memory.short_term import close_redis

    await close_db()
    await close_redis()

    logger = get_logger("main")
    logger.info("All connections closed")


async def run_telegram_bot() -> None:
    """Run the Telegram bot."""
    from app.telegram.bot import create_bot, start_bot

    bot, dp = create_bot()

    shutdown_event = asyncio.Event()

    def signal_handler() -> None:
        logger = get_logger("main")
        logger.info("Shutdown signal received")
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    async def run_with_shutdown():
        await start_bot(bot, dp)

    shutdown_task = asyncio.create_task(shutdown_event.wait())

    bot_task = asyncio.create_task(run_with_shutdown())

    done, pending = await asyncio.wait(
        [bot_task, shutdown_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    for task in pending:
        task.cancel()

    await bot.session.close()


async def run_api_server() -> None:
    """Run the FastAPI server."""
    from app.api.server import create_app

    import uvicorn

    app = create_app()

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8443,
        log_level="info" if not settings.debug else "debug",
        reload=settings.debug,
    )

    server = uvicorn.Server(config)
    await server.serve()


async def run_worker() -> None:
    """Run background worker process."""
    from app.workers.queue import create_arq_settings
    from app.workers.tasks import TASK_HANDLERS
    from arq import run_pool

    logger = get_logger("worker")
    logger.info("Starting background worker...")

    redis_settings = create_arq_settings()

    await run_pool(
        redis_settings=redis_settings,
        functions=TASK_HANDLERS,
        max_jobs=settings.worker.worker_concurrency,
        queue_name=settings.worker.worker_queue_name,
    )


async def main_async(mode: str = "bot") -> None:
    """
    Main async entry point.

    Args:
        mode: Run mode - "bot", "api", "worker", or "all"
    """
    async with lifespan():
        if mode == "bot":
            await run_telegram_bot()
        elif mode == "api":
            await run_api_server()
        elif mode == "worker":
            await run_worker()
        elif mode == "all":
            await asyncio.gather(
                run_telegram_bot(),
                run_api_server(),
            )
        else:
            raise ValueError(f"Unknown mode: {mode}")


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="LumiAI Bot")
    parser.add_argument(
        "--mode",
        "-m",
        choices=["bot", "api", "worker", "all"],
        default="bot",
        help="Run mode (default: bot)",
    )

    args = parser.parse_args()

    try:
        asyncio.run(main_async(args.mode))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()