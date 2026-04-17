"""Background worker queue using arq."""

import json
from typing import Any
import uuid

import redis.asyncio as redis
from arq import Actor
from arq.connections import RedisSettings

from app.config import settings


class WorkerQueue:
    """
    Background task queue using arq.

    Enqueues tasks for heavy operations like:
    - Video processing
    - Large document analysis
    - Deep web research
    - Memory cleanup
    """

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.queue_name = settings.worker.worker_queue_name

    async def enqueue(
        self,
        task_name: str,
        data: dict[str, Any],
        delay: int = 0,
    ) -> str:
        """
        Enqueue a task for background processing.

        Args:
            task_name: Name of the task function
            data: Task data to pass to the function
            delay: Delay in seconds before execution

        Returns:
            task_id: Unique identifier for tracking
        """
        task_id = str(uuid.uuid4())

        job_data = {
            "task_id": task_id,
            "task_name": task_name,
            "data": data,
        }

        if delay > 0:
            await self.redis.zadd(
                f"arq:queue:{self.queue_name}",
                {json.dumps(job_data): 1},
            )
        else:
            await self.redis.rpush(
                f"arq:queue:{self.queue_name}",
                json.dumps(job_data),
            )

        await self.redis.setex(
            f"task:{task_id}",
            86400,
            json.dumps({"status": "queued"}),
        )

        return task_id

    async def enqueue_video_processing(
        self,
        user_id: int,
        chat_id: int,
        video_url: str,
        prompt: str,
        message_id: int,
    ) -> str:
        """Enqueue video processing task."""
        return await self.enqueue(
            "process_video_task",
            {
                "user_id": user_id,
                "chat_id": chat_id,
                "video_url": video_url,
                "prompt": prompt,
                "message_id": message_id,
            },
        )

    async def enqueue_document_processing(
        self,
        user_id: int,
        chat_id: int,
        document_url: str,
        prompt: str,
        message_id: int,
    ) -> str:
        """Enqueue document processing task."""
        return await self.enqueue(
            "process_document_task",
            {
                "user_id": user_id,
                "chat_id": chat_id,
                "document_url": document_url,
                "prompt": prompt,
                "message_id": message_id,
            },
        )

    async def enqueue_web_research(
        self,
        user_id: int,
        chat_id: int,
        query: str,
        message_id: int,
    ) -> str:
        """Enqueue deep web research task."""
        return await self.enqueue(
            "process_web_research_task",
            {
                "user_id": user_id,
                "chat_id": chat_id,
                "query": query,
                "message_id": message_id,
            },
        )

    async def get_task_status(self, task_id: str) -> dict[str, Any] | None:
        """Get current status of a task."""
        data = await self.redis.get(f"task:{task_id}")
        if data:
            return json.loads(data)
        return None

    async def set_task_result(
        self,
        task_id: str,
        status: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        """Set task result/ status."""
        await self.redis.setex(
            f"task:{task_id}",
            3600,
            json.dumps({
                "status": status,
                "result": result,
                "error": error,
            }),
        )

    async def cleanup_completed_tasks(self, max_age: int = 3600) -> int:
        """Remove old completed task records."""
        pattern = "task:*"
        cursor = 0
        deleted = 0

        while True:
            cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
            for key in keys:
                ttl = await self.redis.ttl(key)
                if ttl == -1:
                    await self.redis.delete(key)
                    deleted += 1

            if cursor == 0:
                break

        return deleted


_redis_client: redis.Redis | None = None
_worker_queue: WorkerQueue | None = None


async def get_redis_client() -> redis.Redis:
    """Get or create Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.redis.redis_url,
            encoding="utf-8",
            decode_responses=False,
        )
    return _redis_client


async def close_redis() -> None:
    """Close Redis connection."""
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None


def get_worker_queue(redis_client: redis.Redis) -> WorkerQueue:
    """Create WorkerQueue instance."""
    return WorkerQueue(redis_client)


def create_arq_settings() -> RedisSettings:
    """Create arq Redis settings for worker process."""
    return RedisSettings.from_dsn(settings.redis.redis_url)