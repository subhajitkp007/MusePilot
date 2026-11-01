# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Synchronous Python SDK for the MusePilot HUD API server."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx


class MusePilotError(RuntimeError):
    """Raised when the MusePilot API returns an error payload."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class MusePilotClient:
    """Typed sync client for runs, traces, frames, benchmarks, and voice."""

    def __init__(
        self,
        base_url: str = "http://localhost:8501",
        timeout_seconds: float = 120.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(base_url=self.base_url, timeout=timeout_seconds)
        self._owns_client = client is None

    def close(self) -> None:
        """Release the underlying HTTP client when owned by the SDK."""
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> MusePilotClient:
        """Enter the client context manager."""
        return self

    def __exit__(self, *exc_info: object) -> None:
        """Exit the client context manager, releasing resources."""
        self.close()

    def _raise_for(self, response: httpx.Response, action: str) -> Any:
        """Decode a response or raise MusePilotError with the detail."""
        if response.status_code < 200 or response.status_code >= 300:
            detail = f"{action} failed."
            try:
                body = response.json()
                if isinstance(body, dict) and isinstance(body.get("detail"), str):
                    detail = str(body["detail"])
            except ValueError:
                pass
            raise MusePilotError(detail, status_code=response.status_code)
        if "application/json" in response.headers.get("Content-Type", ""):
            return response.json()
        return response.content

    def health(self) -> dict[str, Any]:
        """Fetch the pre-flight readiness report."""
        return self._raise_for(self._client.get("/api/health"), "Health check")

    def config(self) -> dict[str, Any]:
        """Fetch non-secret runtime configuration."""
        return self._raise_for(self._client.get("/api/config"), "Config fetch")

    def workflows(self) -> list[dict[str, Any]]:
        """List the frozen executable workflows."""
        return self._raise_for(self._client.get("/api/workflows"), "Workflow list")

    def run(
        self,
        workflow_id: str = "w1",
        inject_modal: bool = False,
        custom_intent: str | None = None,
        driver: str = "simulated",
    ) -> dict[str, Any]:
        """Execute a workflow synchronously and return its full trace."""
        payload: dict[str, Any] = {
            "workflow_id": workflow_id,
            "inject_modal": inject_modal,
            "driver": driver,
        }
        if custom_intent is not None:
            payload["custom_intent"] = custom_intent
        return self._raise_for(self._client.post("/api/runs", json=payload), "Workflow run")

    def run_stream(
        self,
        workflow_id: str = "w1",
        inject_modal: bool = False,
        custom_intent: str | None = None,
        driver: str = "simulated",
    ) -> Iterator[dict[str, Any]]:
        """Stream live span events for a run, ending with the final trace."""
        from websockets.sync.client import connect

        ws_url = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
        payload: dict[str, Any] = {
            "workflow_id": workflow_id,
            "inject_modal": inject_modal,
            "driver": driver,
        }
        if custom_intent is not None:
            payload["custom_intent"] = custom_intent
        try:
            with connect(f"{ws_url}/ws/runs") as socket:
                socket.send(json.dumps(payload))
                for raw in socket:
                    event = json.loads(raw)
                    yield event
                    if event.get("type") in ("complete", "error"):
                        return
        except MusePilotError:
            raise
        except Exception as exc:
            raise MusePilotError(f"Run stream failed: {exc}") from exc

    def traces(self, limit: int = 20) -> list[dict[str, Any]]:
        """List recent run-trace summaries, newest first."""
        return self._raise_for(
            self._client.get("/api/traces", params={"limit": limit}), "Trace list"
        )

    def latest_trace(self, workflow_id: str) -> dict[str, Any]:
        """Fetch the golden or latest trace for a workflow."""
        return self._raise_for(
            self._client.get(f"/api/traces/latest/{workflow_id}"), "Latest trace fetch"
        )

    def get_trace(self, trace_id: str) -> dict[str, Any]:
        """Fetch a single trace by ID."""
        return self._raise_for(self._client.get(f"/api/traces/{trace_id}"), "Trace fetch")

    def states(self, workflow: str, trace_id: str | None = None) -> dict[str, Any]:
        """Fetch the visual-state timeline for the frame viewer."""
        params = {"workflow": workflow}
        if trace_id is not None:
            params["trace_id"] = trace_id
        return self._raise_for(
            self._client.get("/api/states", params=params), "State timeline fetch"
        )

    def raw_frame(self, workflow: str, state: str, trace_id: str | None = None) -> bytes:
        """Download a raw canvas frame as PNG bytes."""
        params = {"workflow": workflow, "state": state}
        if trace_id is not None:
            params["trace_id"] = trace_id
        content = self._raise_for(
            self._client.get("/api/frames/raw", params=params), "Raw frame fetch"
        )
        if not isinstance(content, bytes):
            raise MusePilotError("Raw frame fetch returned non-PNG content.")
        return content

    def som_frame(self, workflow: str, state: str, trace_id: str | None = None) -> bytes:
        """Download a Set-of-Mark overlay frame as PNG bytes."""
        params = {"workflow": workflow, "state": state}
        if trace_id is not None:
            params["trace_id"] = trace_id
        content = self._raise_for(
            self._client.get("/api/frames/som", params=params), "SoM frame fetch"
        )
        if not isinstance(content, bytes):
            raise MusePilotError("SoM frame fetch returned non-PNG content.")
        return content

    def benchmark(self) -> dict[str, Any]:
        """Fetch the cumulative benchmark report."""
        return self._raise_for(self._client.get("/api/benchmark"), "Benchmark fetch")

    def transcribe(self, audio_path: Path, workflow_id: str = "w2") -> dict[str, Any]:
        """Transcribe a WAV command file into a voice transcript."""
        with audio_path.open("rb") as handle:
            files = {"audio": (audio_path.name, handle, "audio/wav")}
            data = {"workflow_id": workflow_id}
            return self._raise_for(
                self._client.post("/api/voice/transcribe", files=files, data=data),
                "Voice transcribe",
            )

    def openapi(self) -> dict[str, Any]:
        """Fetch the machine-readable OpenAPI document."""
        return self._raise_for(self._client.get("/api/openapi.json"), "OpenAPI fetch")
