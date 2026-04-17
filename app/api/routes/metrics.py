"""Metrics endpoints for observability."""

from datetime import datetime, timedelta

from fastapi import APIRouter
from pydantic import BaseModel


router = APIRouter()


class MetricValue(BaseModel):
    value: float
    timestamp: datetime


class ProviderMetrics(BaseModel):
    name: str
    total_requests: int
    success_rate: float
    avg_latency_ms: float
    error_count: int


class MetricsResponse(BaseModel):
    timestamp: datetime
    uptime_seconds: float
    requests_total: int
    errors_total: int
    error_rate: float
    providers: list[ProviderMetrics]


_metrics_store: dict[str, list] = {
    "requests": [],
    "errors": [],
    "latency": [],
    "provider_requests": {},
}


@router.get("/metrics")
async def get_metrics() -> MetricsResponse:
    """
    Get current metrics.

    Prometheus-compatible format available at /metrics/prometheus
    """
    global _metrics_store

    now = datetime.utcnow()
    cutoff = now - timedelta(hours=1)

    requests = [r for r in _metrics_store["requests"] if r["timestamp"] > cutoff]
    errors = [e for e in _metrics_store["errors"] if e["timestamp"] > cutoff]

    total_requests = len(requests)
    total_errors = len(errors)
    error_rate = total_errors / total_requests if total_requests > 0 else 0.0

    avg_latency = (
        sum(r.get("latency_ms", 0) for r in requests) / total_requests
        if total_requests > 0
        else 0.0
    )

    provider_metrics = []
    for provider, reqs in _metrics_store["provider_requests"].items():
        provider_errors = len([r for r in reqs if r.get("error")])
        provider_total = len(reqs)
        provider_success_rate = (
            (provider_total - provider_errors) / provider_total if provider_total > 0 else 0.0
        )
        provider_latency = (
            sum(r.get("latency_ms", 0) for r in reqs) / provider_total
            if provider_total > 0
            else 0.0
        )

        provider_metrics.append(
            ProviderMetrics(
                name=provider,
                total_requests=provider_total,
                success_rate=round(provider_success_rate, 4),
                avg_latency_ms=round(provider_latency, 2),
                error_count=provider_errors,
            )
        )

    import time
    uptime = time.time() - _start_time

    return MetricsResponse(
        timestamp=now,
        uptime_seconds=round(uptime, 2),
        requests_total=total_requests,
        errors_total=total_errors,
        error_rate=round(error_rate, 4),
        providers=provider_metrics,
    )


@router.get("/metrics/prometheus")
async def get_prometheus_metrics() -> str:
    """
    Get metrics in Prometheus format.
    """
    metrics = await get_metrics()

    lines = [
        "# HELP lumiai_uptime_seconds Time since application start",
        "# TYPE lumiai_uptime_seconds gauge",
        f"lumiai_uptime_seconds {metrics.uptime_seconds}",
        "",
        "# HELP lumiai_requests_total Total number of requests",
        "# TYPE lumiai_requests_total counter",
        f"lumiai_requests_total {metrics.requests_total}",
        "",
        "# HELP lumiai_errors_total Total number of errors",
        "# TYPE lumiai_errors_total counter",
        f"lumiai_errors_total {metrics.errors_total}",
        "",
        "# HELP lumiai_error_rate Error rate (0-1)",
        "# TYPE lumiai_error_rate gauge",
        f"lumiai_error_rate {metrics.error_rate}",
        "",
    ]

    for provider in metrics.providers:
        lines.extend([
            f"# HELP lumiai_provider_requests_total Requests to {provider.name}",
            f"# TYPE lumiai_provider_requests_total counter",
            f'lumiai_provider_requests_total{{provider="{provider.name}"}} {provider.total_requests}',
            "",
            f"# HELP lumiai_provider_success_rate Success rate for {provider.name}",
            f"# TYPE lumiai_provider_success_rate gauge",
            f'lumiai_provider_success_rate{{provider="{provider.name}"}} {provider.success_rate}',
            "",
            f"# HELP lumiai_provider_latency_ms Average latency for {provider.name}",
            f"# TYPE lumiai_provider_latency_ms gauge",
            f'lumiai_provider_latency_ms{{provider="{provider.name}"}} {provider.avg_latency_ms}',
            "",
        ])

    return "\n".join(lines)


def record_request(provider: str, latency_ms: float, error: bool = False) -> None:
    """Record a request for metrics."""
    global _metrics_store

    now = datetime.utcnow()

    _metrics_store["requests"].append({
        "timestamp": now,
        "provider": provider,
        "latency_ms": latency_ms,
        "error": error,
    })

    if provider not in _metrics_store["provider_requests"]:
        _metrics_store["provider_requests"][provider] = []

    _metrics_store["provider_requests"][provider].append({
        "timestamp": now,
        "latency_ms": latency_ms,
        "error": error,
    })

    if error:
        _metrics_store["errors"].append({"timestamp": now, "provider": provider})


import time

_start_time = time.time()