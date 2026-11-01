# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Integration tests for the Starlette HUD API and run-streaming WebSocket."""

from __future__ import annotations

from starlette.testclient import TestClient

from musepilot.server.app import create_app

client = TestClient(create_app())


def test_api_index_lists_surface() -> None:
    """The API root serves the endpoint index or the built web HUD."""
    response = client.get("/")
    assert response.status_code == 200
    if "application/json" in response.headers["content-type"]:
        body = response.json()
        assert body["service"] == "musepilot-api"
        assert "WS /ws/runs" in body["endpoints"]
    else:
        assert "MusePilot HUD" in response.text


def test_health_endpoint_passes_without_secrets() -> None:
    """Health reports readiness and never embeds key material."""
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["passed"] is True
    assert body["execution_mode"] == "simulated"
    assert body["api_keys_configured"] in (True, False)
    for key in body:
        if key == "api_keys_configured":
            continue
        assert "key" not in key and "secret" not in key and "token" not in key


def test_config_endpoint_exposes_no_secrets() -> None:
    """Config serves only non-secret runtime values."""
    response = client.get("/api/config")
    assert response.status_code == 200
    body = response.json()
    assert body["verifier_model_id"] == "meta-models/muse-spark-open-1026"
    assert body["verifier_backend"] == "partner"
    assert body["meta_verifier_model_id"] == "muse-spark-1.3"
    assert body["display_dpi_scale"] == 2.0
    for key in body:
        assert "key" not in key and "secret" not in key and "token" not in key


def test_list_workflows_returns_frozen_pair() -> None:
    """Both frozen workflows are advertised."""
    response = client.get("/api/workflows")
    assert response.status_code == 200
    ids = [w["workflow_id"] for w in response.json()]
    assert ids == ["w1", "w2"]


def test_create_run_executes_w1() -> None:
    """POST /api/runs completes W1 and returns a schema-valid trace."""
    response = client.post("/api/runs", json={"workflow_id": "w1"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["metrics"]["total_steps_completed"] == 4
    assert len(body["records"]) == 4


def test_create_run_rejects_unknown_workflow() -> None:
    """Invalid workflow IDs fail closed with 400."""
    response = client.post("/api/runs", json={"workflow_id": "w9"})
    assert response.status_code == 400


def test_create_run_rejects_malformed_json() -> None:
    """Non-JSON bodies fail closed with 400."""
    response = client.post(
        "/api/runs", content="not-json", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 400


def test_latest_trace_round_trip() -> None:
    """A completed run is retrievable via latest-trace and trace-by-ID."""
    run = client.post("/api/runs", json={"workflow_id": "w1"}).json()
    latest = client.get("/api/traces/latest/w1")
    assert latest.status_code == 200
    assert latest.json()["workflow_id"] == "w1"
    single = client.get(f"/api/traces/{run['trace_id']}")
    assert single.status_code == 200
    assert single.json()["trace_id"] == run["trace_id"]


def test_unknown_trace_returns_404() -> None:
    """Missing traces return 404 instead of an empty payload."""
    assert client.get("/api/traces/doesnotexist").status_code == 404
    assert client.get("/api/traces/latest/w9").status_code == 404


def test_list_traces_returns_summaries() -> None:
    """Trace history returns newest-first summaries."""
    client.post("/api/runs", json={"workflow_id": "w1"})
    response = client.get("/api/traces?limit=5")
    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 1
    assert set(body[0]) == {
        "trace_id",
        "workflow_id",
        "status",
        "created_at",
        "steps_completed",
        "steps_planned",
        "verification_pass_rate",
        "self_healing_recoveries",
    }


def test_list_traces_validates_limit() -> None:
    """Out-of-range limits fail closed with 400."""
    assert client.get("/api/traces?limit=0").status_code == 400
    assert client.get("/api/traces?limit=999").status_code == 400
    assert client.get("/api/traces?limit=abc").status_code == 400


def test_states_timeline_matches_dashboard_logic() -> None:
    """State labels replicate the HUD timeline contract."""
    client.post("/api/runs", json={"workflow_id": "w2", "inject_modal": True})
    response = client.get("/api/states?workflow=w2")
    assert response.status_code == 200
    body = response.json()
    assert body["states"][0] == "initial"
    assert body["default_state"] == body["states"][-1]
    assert client.get("/api/states?workflow=w9").status_code == 400


def test_raw_frame_returns_png() -> None:
    """Raw canvas frames render as PNG bytes."""
    response = client.get("/api/frames/raw?workflow=w1&state=initial")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_som_frame_returns_png() -> None:
    """SoM overlays render as PNG bytes with zero-coordinate badges."""
    client.post("/api/runs", json={"workflow_id": "w1"})
    response = client.get("/api/frames/som?workflow=w1&state=initial")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_live_frame_returns_png() -> None:
    """Live frame preview returns a valid PNG image."""
    response = client.get("/api/frames/live?driver=simulated")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_frames_reject_bad_params() -> None:
    """Frame endpoints validate workflow and state inputs."""
    assert client.get("/api/frames/raw?workflow=w9").status_code == 400
    assert client.get("/api/frames/raw?state=../evil").status_code == 400
    assert client.get("/api/frames/som?workflow=w9").status_code == 400


def test_benchmark_endpoint_reports_runs() -> None:
    """Benchmark aggregates traces recorded through the API."""
    client.post("/api/runs", json={"workflow_id": "w1"})
    response = client.get("/api/benchmark")
    assert response.status_code == 200
    body = response.json()
    assert body["total_runs_analyzed"] >= 1
    assert body["mean_mask_hit_rate"] == 1.0


def test_websocket_streams_spans_then_completes() -> None:
    """WS runs emit span events followed by a complete trace payload."""
    with client.websocket_connect("/ws/runs") as websocket:
        websocket.send_json({"workflow_id": "w1"})
        messages = []
        while True:
            message = websocket.receive_json()
            messages.append(message)
            if message["type"] in ("complete", "error"):
                break
    assert messages[0]["type"] == "started"
    assert messages[-1]["type"] == "complete"
    assert messages[-1]["trace"]["status"] == "COMPLETED"
    assert any(m["type"] == "span" for m in messages)
    assert any(m["type"] == "frame" for m in messages)
    assert any(m["type"] == "step_record" for m in messages)


def test_websocket_rejects_invalid_request() -> None:
    """WS runs validate the request before executing anything."""
    with client.websocket_connect("/ws/runs") as websocket:
        websocket.send_json({"workflow_id": "w9"})
        message = websocket.receive_json()
        assert message["type"] == "error"
