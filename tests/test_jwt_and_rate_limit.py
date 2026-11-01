# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Comprehensive security tests for JWT authentication and Meta-grade rate limiting."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient

from musepilot.config import MusePilotSettings
from musepilot.security import (
    ExpiredSignatureError,
    InvalidTokenError,
    SlidingWindowRateLimiter,
    decode_and_verify_jwt,
    generate_jwt,
)
from musepilot.server.app import create_app


def test_jwt_generation_and_decoding():
    """Verify standard JWT generation and cryptographic verification."""
    secret = "meta-security-test-key-32-bytes"
    payload = {"sub": "meta-operator", "role": "admin", "iss": "musepilot"}
    token = generate_jwt(payload, secret=secret, expires_in_seconds=3600)

    # Token must be 3 dot-separated base64url segments
    parts = token.split(".")
    assert len(parts) == 3

    decoded = decode_and_verify_jwt(token, secret=secret, issuer="musepilot")
    assert decoded["sub"] == "meta-operator"
    assert decoded["role"] == "admin"
    assert decoded["iss"] == "musepilot"
    assert "iat" in decoded
    assert "exp" in decoded


def test_jwt_expired_token_rejected():
    """Verify expired JWTs are rejected with ExpiredSignatureError."""
    secret = "meta-security-test-key-32-bytes"
    token = generate_jwt({"sub": "expired-user"}, secret=secret, expires_in_seconds=-100)

    with pytest.raises(ExpiredSignatureError) as exc_info:
        decode_and_verify_jwt(token, secret=secret, leeway_seconds=0)
    assert "expired" in str(exc_info.value).lower()


def test_jwt_tampered_signature_rejected():
    """Verify forged signatures and wrong secrets fail closed with InvalidTokenError."""
    secret = "meta-security-test-key-32-bytes"
    token = generate_jwt({"sub": "valid-user"}, secret=secret, expires_in_seconds=3600)

    # 1. Verification with wrong secret must fail
    with pytest.raises(InvalidTokenError):
        decode_and_verify_jwt(token, secret="attacker-wrong-secret")

    # 2. Tampered payload segment must fail
    parts = token.split(".")
    tampered = f"{parts[0]}.eyJzdWIiOiJoYWNrZXIifQ.{parts[2]}"
    with pytest.raises(InvalidTokenError):
        decode_and_verify_jwt(tampered, secret=secret)


def test_sliding_window_rate_limiter_precision():
    """Verify sliding window counter accurately permits and throttles requests."""
    limiter = SlidingWindowRateLimiter(default_window_seconds=1.0)
    client_key = "10.0.0.1:test"

    # Allow up to 3 requests
    allowed1, rem1, _ = limiter.check(client_key, limit=3, window_seconds=1.0)
    allowed2, rem2, _ = limiter.check(client_key, limit=3, window_seconds=1.0)
    allowed3, rem3, _ = limiter.check(client_key, limit=3, window_seconds=1.0)

    assert allowed1 is True and rem1 == 2
    assert allowed2 is True and rem2 == 1
    assert allowed3 is True and rem3 == 0

    # 4th request in the same window must be blocked
    allowed4, rem4, retry_after = limiter.check(client_key, limit=3, window_seconds=1.0)
    assert allowed4 is False
    assert rem4 == 0
    assert retry_after >= 1

    # Wait for window to slide past
    time.sleep(1.1)
    allowed5, rem5, _ = limiter.check(client_key, limit=3, window_seconds=1.0)
    assert allowed5 is True
    assert rem5 == 2


def test_rate_limit_middleware_returns_429_and_headers():
    """Verify HTTP 429 Too Many Requests response and standard RFC headers."""
    custom_limiter = SlidingWindowRateLimiter(default_window_seconds=60.0)
    settings = MusePilotSettings(
        rate_limit_enabled=True,
        rate_limit_read_per_minute=2,  # Tight limit: 2 requests
    )
    app = create_app(settings=settings)
    # Inject our isolated test limiter into app middleware
    for middleware in app.user_middleware:
        if hasattr(middleware, "kwargs") and "limiter" in middleware.kwargs:
            middleware.kwargs["limiter"] = custom_limiter

    client = TestClient(app)

    # Request 1: OK
    resp1 = client.get("/api/workflows")
    assert resp1.status_code == 200
    assert resp1.headers.get("x-ratelimit-limit") == "2"
    assert resp1.headers.get("x-ratelimit-remaining") == "1"

    # Request 2: OK
    resp2 = client.get("/api/workflows")
    assert resp2.status_code == 200
    assert resp2.headers.get("x-ratelimit-remaining") == "0"

    # Request 3: Throttled with 429
    resp3 = client.get("/api/workflows")
    assert resp3.status_code == 429
    assert resp3.headers.get("retry-after") is not None
    assert resp3.headers.get("x-ratelimit-remaining") == "0"
    body = resp3.json()
    assert "Rate limit exceeded" in body["detail"]
    assert "retry_after" in body


def test_rate_limit_exempts_health_endpoint():
    """Verify health checks remain exempt from rate limiting for monitor liveness."""
    settings = MusePilotSettings(
        rate_limit_enabled=True,
        rate_limit_read_per_minute=1,
    )
    app = create_app(settings=settings)
    client = TestClient(app)

    # Consecutive requests to /api/health and /health should never 429
    for path in ("/api/health", "/api/health/", "/health", "/health/"):
        for _ in range(3):
            resp = client.get(path)
            assert resp.status_code == 200


def test_jwt_auth_via_secret_in_app():
    """Verify requests authenticate successfully when valid JWT is signed by MUSEPILOT_JWT_SECRET."""
    secret = "enterprise-production-signing-secret"
    settings = MusePilotSettings(jwt_secret=secret)
    app = create_app(settings=settings)
    client = TestClient(app)

    # 1. Unauthenticated request rejected
    resp = client.post("/api/runs", json={"workflow_id": "w1"})
    assert resp.status_code == 401
    assert "Unauthorized" in resp.json()["detail"]

    # 2. Token signed with wrong secret rejected
    bad_token = generate_jwt({"sub": "operator"}, secret="unauthorized-secret")
    resp = client.post(
        "/api/runs",
        json={"workflow_id": "w1"},
        headers={"Authorization": f"Bearer {bad_token}"},
    )
    assert resp.status_code == 401

    # 3. Token signed with correct secret accepted
    valid_token = generate_jwt({"sub": "authorized-operator"}, secret=secret)
    mock_trace = MagicMock()
    mock_trace.model_dump.return_value = {"trace_id": "jwt_auth_trace", "status": "COMPLETED"}

    with patch("musepilot.server.app._execute_run_blocking") as mock_exec:
        mock_exec.return_value = mock_trace
        resp = client.post(
            "/api/runs",
            json={"workflow_id": "w1"},
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "COMPLETED"


def test_jwt_auth_via_static_token_in_env():
    """Verify requests authenticate when static JWT token string is provided in .env."""
    static_token = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzdWIiOiJzdGF0aWMtb3BlcmF0b3IiLCJleHAiOjE5OTk5OTk5OTl9."
        "mock_signature_hash"
    )
    settings = MusePilotSettings(jwt_token=static_token)
    app = create_app(settings=settings)
    client = TestClient(app)

    mock_trace = MagicMock()
    mock_trace.model_dump.return_value = {"trace_id": "static_jwt_trace", "status": "COMPLETED"}

    with patch("musepilot.server.app._execute_run_blocking") as mock_exec:
        mock_exec.return_value = mock_trace

        # Bearer header
        resp = client.post(
            "/api/runs",
            json={"workflow_id": "w1"},
            headers={"Authorization": f"Bearer {static_token}"},
        )
        assert resp.status_code == 200

        # X-API-Key header
        resp = client.post(
            "/api/runs",
            json={"workflow_id": "w1"},
            headers={"X-API-Key": static_token},
        )
        assert resp.status_code == 200

        # Query param ?token=
        resp = client.post(
            f"/api/runs?token={static_token}",
            json={"workflow_id": "w1"},
        )
        assert resp.status_code == 200


def test_frontend_cookie_session_handshake_without_knowing_jwt():
    """Verify frontend browser can authenticate transparently via HttpOnly cookie."""
    secret = "enterprise-browser-secret-key-12345"
    settings = MusePilotSettings(jwt_secret=secret)
    app = create_app(settings=settings)
    client = TestClient(app)

    # 1. Frontend calls /api/auth/token (or loads index.html)
    resp = client.get("/api/auth/token")
    assert resp.status_code == 200
    assert "musepilot_jwt" in resp.cookies

    # 2. Frontend calls POST /api/runs using the cookie without knowing/passing JWT header
    mock_trace = MagicMock()
    mock_trace.model_dump.return_value = {"trace_id": "cookie_trace", "status": "COMPLETED"}

    with patch("musepilot.server.app._execute_run_blocking") as mock_exec:
        mock_exec.return_value = mock_trace
        # TestClient automatically includes cookies received in step 1
        resp = client.post("/api/runs", json={"workflow_id": "w1"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "COMPLETED"


def test_websocket_rate_limit_rejection():
    """Verify WebSocket connections enforce mutation rate limit quota."""
    from musepilot.security import GLOBAL_RATE_LIMITER

    GLOBAL_RATE_LIMITER.reset()
    settings = MusePilotSettings(
        rate_limit_enabled=True,
        rate_limit_mutation_per_minute=1,  # Only 1 connection allowed
    )
    app = create_app(settings=settings)
    client = TestClient(app)

    # First connection should connect
    with client.websocket_connect("/ws/runs"):
        # Second connection from same IP in same minute must be rejected with 4429
        with client.websocket_connect("/ws/runs") as ws2:
            msg = ws2.receive_json()
            assert msg["type"] == "error"
            assert "Rate limit exceeded" in msg["detail"]
