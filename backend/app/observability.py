from __future__ import annotations

from collections import Counter
from threading import Lock
from time import monotonic

from starlette.types import ASGIApp, Message, Receive, Scope, Send

LATENCY_BUCKETS_MS = (100, 500, 2_000)


class RuntimeTelemetry:
    """Bounded, process-local HTTP telemetry without request data or identifiers."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._started_at = monotonic()
        self._total_requests = 0
        self._inflight_requests = 0
        self._max_inflight_requests = 0
        self._total_duration_ms = 0.0
        self._status_families: Counter[str] = Counter()
        self._latency_buckets: Counter[str] = Counter()

    def begin(self) -> float:
        with self._lock:
            self._inflight_requests += 1
            self._max_inflight_requests = max(
                self._max_inflight_requests, self._inflight_requests
            )
        return monotonic()

    def finish(self, started_at: float, status_code: int) -> None:
        duration_ms = max(0.0, (monotonic() - started_at) * 1_000)
        family = f"{max(1, min(5, status_code // 100))}xx"
        if duration_ms < LATENCY_BUCKETS_MS[0]:
            bucket = "lt_100_ms"
        elif duration_ms < LATENCY_BUCKETS_MS[1]:
            bucket = "100_to_499_ms"
        elif duration_ms < LATENCY_BUCKETS_MS[2]:
            bucket = "500_to_1999_ms"
        else:
            bucket = "gte_2000_ms"
        with self._lock:
            self._inflight_requests = max(0, self._inflight_requests - 1)
            self._total_requests += 1
            self._total_duration_ms += duration_ms
            self._status_families[family] += 1
            self._latency_buckets[bucket] += 1

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            average = (
                self._total_duration_ms / self._total_requests
                if self._total_requests
                else 0.0
            )
            return {
                "uptime_seconds": round(max(0.0, monotonic() - self._started_at), 3),
                "total_requests": self._total_requests,
                "inflight_requests": self._inflight_requests,
                "max_inflight_requests": self._max_inflight_requests,
                "average_duration_ms": round(average, 3),
                "status_families": {
                    family: self._status_families.get(family, 0)
                    for family in ("1xx", "2xx", "3xx", "4xx", "5xx")
                },
                "latency_buckets": {
                    bucket: self._latency_buckets.get(bucket, 0)
                    for bucket in (
                        "lt_100_ms",
                        "100_to_499_ms",
                        "500_to_1999_ms",
                        "gte_2000_ms",
                    )
                },
            }


runtime_telemetry = RuntimeTelemetry()


class RuntimeTelemetryMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started_at = runtime_telemetry.begin()
        status_code = 500

        async def capture_status(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
            await send(message)

        try:
            await self.app(scope, receive, capture_status)
        finally:
            runtime_telemetry.finish(started_at, status_code)
