"""Worker pool management for scaling background workers."""

import asyncio
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import Any, Callable
from contextlib import asynccontextmanager

from app.config import settings


class WorkerPool:
    """
    Manages worker pools for CPU and I/O bound tasks.

    CPU-bound tasks: video processing, document parsing
    I/O-bound tasks: web requests, file operations
    """

    def __init__(
        self,
        max_workers: int | None = None,
        cpu_bound: bool = False,
    ):
        self.max_workers = max_workers or settings.worker.worker_concurrency
        self.cpu_bound = cpu_bound
        self._executor: ThreadPoolExecutor | ProcessPoolExecutor | None = None

    def _get_executor(self) -> ThreadPoolExecutor | ProcessPoolExecutor:
        """Get or create the executor."""
        if self._executor is None:
            if self.cpu_bound:
                self._executor = ProcessPoolExecutor(max_workers=self.max_workers)
            else:
                self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        return self._executor

    async def run(self, fn: Callable, *args: Any, **kwargs: Any) -> Any:
        """Run a function in the worker pool."""
        executor = self._get_executor()
        loop = asyncio.get_event_loop()

        if asyncio.iscoroutinefunction(fn):
            return await fn(*args, **kwargs)

        return await loop.run_in_executor(
            executor,
            lambda: fn(*args, **kwargs),
        )

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the worker pool."""
        if self._executor:
            self._executor.shutdown(wait=wait)
            self._executor = None


class VideoProcessingPool(WorkerPool):
    """Specialized pool for video processing tasks."""

    def __init__(self):
        super().__init__(cpu_bound=True)


class IOBoundPool(WorkerPool):
    """Specialized pool for I/O bound tasks."""

    def __init__(self):
        super().__init__(cpu_bound=False)


_global_pools: dict[str, WorkerPool] = {}


def get_worker_pool(name: str = "default") -> WorkerPool:
    """Get or create a named worker pool."""
    if name not in _global_pools:
        if name == "video":
            _global_pools[name] = VideoProcessingPool()
        elif name == "io":
            _global_pools[name] = IOBoundPool()
        else:
            _global_pools[name] = WorkerPool()
    return _global_pools[name]


def shutdown_all_pools() -> None:
    """Shutdown all worker pools."""
    for pool in _global_pools.values():
        pool.shutdown()
    _global_pools.clear()