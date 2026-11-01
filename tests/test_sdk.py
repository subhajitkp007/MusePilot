# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Tests for the Python SDK, OpenAPI document, and ref integrity."""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import httpx
import pytest
from starlette.testclient import TestClient

from musepilot.sdk import MusePilotClient, MusePilotError
from musepilot.server.app import create_app

server = TestClient(create_app())


def _sdk(handler: object) -> MusePilotClient:
    """Build an SDK client routed through a mock transport."""
    transport = httpx.MockTransport(handler)  # type: ignore[arg-type]
    return MusePilotClient(
        base_url="http://test",
        client=httpx.Client(transport=transport, base_url="http://test"),
    )


def test_sdk_health_and_config() -> None:
    """SDK decodes health and config payloads."""
    sdk = _sdk(
        lambda request: httpx.Response(200, json={"passed": True, "execution_mode": "simulated"})
    )
    assert sdk.health()["passed"] is True
    assert sdk.config()["execution_mode"] == "simulated"


def test_sdk_run_posts_payload() -> None:
    """SDK run posts workflow fields and returns the trace dict."""
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content.decode("utf-8")))
        return httpx.Response(200, json={"trace_id": "abc", "status": "COMPLETED"})

    sdk = _sdk(handler)
    trace = sdk.run("w2", inject_modal=True)
    assert trace["trace_id"] == "abc"
    assert seen == {"workflow_id": "w2", "inject_modal": True, "driver": "simulated"}
    traced = sdk.run("w1", custom_intent="hi")
    assert traced["status"] == "COMPLETED"
    assert seen["custom_intent"] == "hi"


def test_sdk_reads_traces_frames_benchmark() -> None:
    """SDK read methods hit the right paths and decode bodies."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/api/traces":
            return httpx.Response(200, json=[{"trace_id": "a"}])
        if path == "/api/traces/latest/w1":
            return httpx.Response(200, json={"trace_id": "a"})
        if path == "/api/traces/a":
            return httpx.Response(200, json={"trace_id": "a"})
        if path == "/api/states":
            return httpx.Response(200, json={"states": ["initial"], "default_state": "initial"})
        if path in ("/api/frames/raw", "/api/frames/som"):
            return httpx.Response(200, headers={"Content-Type": "image/png"}, content=b"\x89PNG")
        if path == "/api/benchmark":
            return httpx.Response(200, json={"total_runs_analyzed": 3})
        if path == "/api/workflows":
            return httpx.Response(200, json=[{"workflow_id": "w1"}])
        raise AssertionError(f"unexpected path {path}")

    sdk = _sdk(handler)
    assert sdk.traces()[0]["trace_id"] == "a"
    assert sdk.latest_trace("w1")["trace_id"] == "a"
    assert sdk.get_trace("a")["trace_id"] == "a"
    assert sdk.states("w1")["default_state"] == "initial"
    assert sdk.raw_frame("w1", "initial") == b"\x89PNG"
    assert sdk.som_frame("w1", "initial") == b"\x89PNG"
    assert sdk.benchmark()["total_runs_analyzed"] == 3
    assert sdk.workflows()[0]["workflow_id"] == "w1"


def test_sdk_transcribe_uploads_wav(tmp_path: Path) -> None:
    """SDK transcribe posts multipart audio and returns the transcript."""
    audio = tmp_path / "cmd.wav"
    audio.write_bytes(b"RIFF....WAVE")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/voice/transcribe"
        assert 'name="audio"' in request.content.decode("latin-1")
        return httpx.Response(200, json={"transcript": "do it", "confidence": 0.99})

    sdk = _sdk(handler)
    assert sdk.transcribe(audio)["transcript"] == "do it"


def test_sdk_error_mapping() -> None:
    """HTTP errors surface details and status codes."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"detail": "bad workflow"})

    sdk = _sdk(handler)
    with pytest.raises(MusePilotError, match="bad workflow") as exc_info:
        sdk.latest_trace("w9")
    assert exc_info.value.status_code == 400


def test_sdk_context_manager_closes_owned_client() -> None:
    """The context manager releases owned HTTP resources."""
    with MusePilotClient(base_url="http://test") as sdk:
        assert sdk.base_url == "http://test"
    assert sdk._client.is_closed


def test_sdk_run_stream_yields_until_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    """run_stream yields span events and stops at complete."""
    messages = [
        json.dumps({"type": "started", "workflow_id": "w1"}),
        json.dumps({"type": "span", "span": {"name": "perception.sam3_1"}}),
        json.dumps({"type": "complete", "trace": {"trace_id": "abc"}}),
    ]

    class FakeSocket:
        def __init__(self) -> None:
            self.sent: list[str] = []

        def __enter__(self) -> FakeSocket:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def send(self, payload: str) -> None:
            self.sent.append(payload)

        def __iter__(self):  # type: ignore[no-untyped-def]
            return iter(messages)

    sockets: list[FakeSocket] = []

    def fake_connect(url: str) -> FakeSocket:
        assert url == "ws://test/ws/runs"
        sockets.append(FakeSocket())
        return sockets[0]

    module = types.ModuleType("websockets.sync.client")
    module.connect = fake_connect  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "websockets.sync.client", module)
    sdk = MusePilotClient(base_url="http://test")
    events = list(sdk.run_stream("w1"))
    assert [e["type"] for e in events] == ["started", "span", "complete"]
    assert json.loads(sockets[0].sent[0])["workflow_id"] == "w1"


def test_openapi_document_refs_resolve() -> None:
    """Every $ref in the served OpenAPI document resolves to a schema."""
    response = server.get("/api/openapi.json")
    assert response.status_code == 200
    doc = response.json()
    assert doc["openapi"] == "3.1.0"
    assert "/api/runs" in doc["paths"]
    assert "/api/voice/transcribe" in doc["paths"]
    schemas = doc["components"]["schemas"]
    assert {"RunRequest", "RunTrace", "TraceSummary", "VoiceTranscript"}.issubset(schemas)

    def refs(node: object) -> list[str]:
        found: list[str] = []
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "$ref" and isinstance(value, str):
                    found.append(value)
                else:
                    found.extend(refs(value))
        elif isinstance(node, list):
            for item in node:
                found.extend(refs(item))
        return found

    for ref in refs(doc["paths"]):
        name = ref.removeprefix("#/components/schemas/")
        assert name in schemas, f"dangling $ref {ref}"
    assert "target_mask_id" in json.dumps(schemas["StepNode"])


def test_sdk_openapi_round_trip() -> None:
    """SDK openapi() decodes the served document."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/openapi.json"
        return httpx.Response(200, json={"openapi": "3.1.0"})

    assert _sdk(handler).openapi()["openapi"] == "3.1.0"
