# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Industry-standard sliding window rate limiter and ASGI middleware."""

from __future__ import annotations

import json
import threading
import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any


class SlidingWindowRateLimiter:
    """Thread-safe sliding window log rate limiter.

    Maintains high precision with zero boundary burst vulnerability by recording
    timestamp logs within each dynamic rolling window.
    """

    def __init__(self, default_window_seconds: float = 60.0) -> None:
        self.default_window_seconds = default_window_seconds
        self._records: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()
        self._access_counter: int = 0

    def check(
        self,
        key: str,
        limit: int,
        window_seconds: float | None = None,
    ) -> tuple[bool, int, int]:
        """Check if request is permitted under rate limit.

        Args:
            key: Rate limit partition identifier (e.g., '192.168.1.1:read').
            limit: Maximum allowed requests within the sliding window.
            window_seconds: Rolling window duration (defaults to 60.0s).

        Returns:
            Tuple of (allowed: bool, remaining: int, reset_or_retry: int).
            When allowed: reset_or_retry is the Unix timestamp when the window clears.
            When rejected: reset_or_retry is the retry_after seconds to wait.
        """
        win = window_seconds or self.default_window_seconds
        now = time.time()
        cutoff = now - win

        with self._lock:
            self._access_counter += 1
            if self._access_counter >= 1000:
                self._prune_expired_locked(cutoff)
                self._access_counter = 0

            timestamps = self._records[key]
            # Retain only entries within active window
            active = [t for t in timestamps if t > cutoff]
            self._records[key] = active

            if len(active) >= limit:
                # Quota exhausted: retry_after is the duration until oldest drops off
                oldest = active[0]
                retry_after = max(1, int(oldest + win - now) + 1)
                return False, 0, retry_after

            # Allow request and record current timestamp
            active.append(now)
            remaining = max(0, limit - len(active))
            reset_epoch = int(now + win)
            return True, remaining, reset_epoch

    def reset(self, key: str | None = None) -> None:
        """Clear all or specific rate limit counters."""
        with self._lock:
            if key is None:
                self._records.clear()
            else:
                self._records.pop(key, None)

    def _prune_expired_locked(self, cutoff: float) -> None:
        """Remove keys with no active timestamps (invoked while holding lock)."""
        expired_keys = [
            k
            for k, timestamps in self._records.items()
            if not timestamps or timestamps[-1] <= cutoff
        ]
        for k in expired_keys:
            del self._records[k]


GLOBAL_RATE_LIMITER = SlidingWindowRateLimiter()


class RateLimitMiddleware:
    """Starlette ASGI middleware enforcing industry-standard Meta-grade rate limits."""

    def __init__(
        self,
        app: Any,
        limiter: SlidingWindowRateLimiter | None = None,
        settings_getter: Callable[[], Any] | None = None,
    ) -> None:
        self.app = app
        self.limiter = limiter or GLOBAL_RATE_LIMITER
        self.settings_getter = settings_getter

    def _get_client_ip(self, scope: dict[str, Any]) -> str:
        """Extract client IP respecting X-Forwarded-For header if present."""
        headers = dict(scope.get("headers", []))
        xff = headers.get(b"x-forwarded-for")
        if xff:
            try:
                # Pick leftmost IP from proxy chain
                return xff.decode("latin1").split(",")[0].strip()
            except (UnicodeDecodeError, IndexError, ValueError):
                return "127.0.0.1"
        client = scope.get("client")
        if client and len(client) > 0:
            return str(client[0])
        return "127.0.0.1"

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        from musepilot.config import get_settings

        settings = self.settings_getter() if self.settings_getter else get_settings()
        if not getattr(settings, "rate_limit_enabled", True):
            await self.app(scope, receive, send)
            return

        raw_path = scope.get("path", "")
        normalized_path = raw_path.rstrip("/")
        method = scope.get("method", "GET").upper()

        # Explicitly exempt health check endpoints (/api/health, /health) from all rate limits
        # ensuring infrastructure probes, container orchestrators, and HUD heartbeats are never throttled.
        if (
            normalized_path in ("/api/health", "/health")
            or normalized_path == ""
            or normalized_path.startswith("/_stcore")
            or normalized_path.startswith("/assets")
            or not normalized_path.startswith("/api/")
        ):
            await self.app(scope, receive, send)
            return

        path = raw_path

        # Determine rate limit tier
        ip = self._get_client_ip(scope)
        if method == "POST" and (path == "/api/runs" or path == "/api/voice/transcribe"):
            tier = "mutation"
            limit = getattr(settings, "rate_limit_mutation_per_minute", 30)
        else:
            tier = "read"
            limit = getattr(settings, "rate_limit_read_per_minute", 120)

        key = f"{ip}:{tier}"
        allowed, remaining, reset_or_retry = self.limiter.check(key=key, limit=limit)

        if not allowed:
            # 429 Too Many Requests response
            retry_after = reset_or_retry
            error_body = json.dumps(
                {
                    "detail": f"Rate limit exceeded ({limit} requests/minute). Please slow down.",
                    "retry_after": retry_after,
                }
            ).encode("utf-8")

            headers = [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(error_body)).encode("ascii")),
                (b"retry-after", str(retry_after).encode("ascii")),
                (b"x-ratelimit-limit", str(limit).encode("ascii")),
                (b"x-ratelimit-remaining", b"0"),
                (b"x-ratelimit-reset", str(int(time.time() + retry_after)).encode("ascii")),
            ]

            await send({"type": "http.response.start", "status": 429, "headers": headers})
            await send({"type": "http.response.body", "body": error_body})
            return

        # Inject standard rate limit headers on allowed responses
        async def send_with_ratelimit_headers(message: Any) -> None:
            if message["type"] == "http.response.start":
                resp_headers = list(message.get("headers", []))
                resp_headers.append((b"x-ratelimit-limit", str(limit).encode("ascii")))
                resp_headers.append((b"x-ratelimit-remaining", str(remaining).encode("ascii")))
                resp_headers.append((b"x-ratelimit-reset", str(reset_or_retry).encode("ascii")))
                message["headers"] = resp_headers
            await send(message)

        await self.app(scope, receive, send_with_ratelimit_headers)
