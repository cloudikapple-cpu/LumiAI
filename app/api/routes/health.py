"""Health check endpoints."""

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.base import engine
from app.memory.short_term import get_redis_client


router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    services: dict


class ServiceHealth(BaseModel):
    status: str
    latency_ms: float | None = None


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint.

    Returns status of all services.
    """
    services = {
        "database": await _check_database(),
        "redis": await _check_redis(),
    }

    all_healthy = all(s.status == "healthy" for s in services.values())

    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        timestamp=datetime.utcnow(),
        services={
            name: {"status": s.status, "latency_ms": s.latency_ms}
            for name, s in services.items()
        },
    )


@router.get("/health/live")
async def liveness() -> dict:
    """
    Kubernetes liveness probe.

    Returns 200 if the application is running.
    """
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness() -> dict:
    """
    Kubernetes readiness probe.

    Returns 200 if the application is ready to accept traffic.
    """
    try:
        db_health = await _check_database()
        redis_health = await _check_redis()

        if db_health.status == "healthy" and redis_health.status == "healthy":
            return {"status": "ready"}

        raise HTTPException(status_code=503, detail="Services not ready")

    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


async def _check_database() -> ServiceHealth:
    """Check database connectivity."""
    import time
    from sqlalchemy import text

    if engine is None:
        return ServiceHealth(status="unavailable", latency_ms=None)

    try:
        start = time.perf_counter()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        latency = (time.perf_counter() - start) * 1000

        return ServiceHealth(status="healthy", latency_ms=round(latency, 2))

    except Exception as e:
        return ServiceHealth(status="unhealthy", latency_ms=None)


async def _check_redis() -> ServiceHealth:
    """Check Redis connectivity."""
    import time

    try:
        redis_client = await get_redis_client()

        start = time.perf_counter()
        await redis_client.ping()
        latency = (time.perf_counter() - start) * 1000

        return ServiceHealth(status="healthy", latency_ms=round(latency, 2))

    except Exception:
        return ServiceHealth(status="unhealthy", latency_ms=None)