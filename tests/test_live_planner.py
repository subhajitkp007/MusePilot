# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Focused tests for live Muse Spark planning: JSON repair and error honesty."""

from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
import pytest
from PIL import Image

from musepilot.contracts.repair import extract_json_object
from musepilot.contracts.schemas import LiveModelError, MaskMetadata, MaskSet
from musepilot.planning.spark_planner import MuseSparkPlanner

_DAG = {
    "plan_version": "planner_som_v1",
    "workflow_id": "live",
    "intent": "Click the login button.",
    "plan_summary": "Click login",
    "steps": [
        {
            "step_id": 1,
            "operation": "click",
            "target_mask_id": 1,
            "expected_outcome": "Login dialog opens",
            "reasoning": "Mask 1 is the login button.",
        }
    ],
}


def _mask_set() -> MaskSet:
    """Build a two-mask set for planner validation."""
    return MaskSet(
        screen_hash="abc",
        width_px=800,
        height_px=600,
        masks=[
            MaskMetadata(
                mask_id=1,
                bbox=(10, 10, 100, 40),
                centroid_px=(55, 25),
                area_px=2700,
                confidence=0.95,
            ),
            MaskMetadata(
                mask_id=2,
                bbox=(10, 60, 100, 90),
                centroid_px=(55, 75),
                area_px=2700,
                confidence=0.94,
            ),
        ],
    )


def _chat_response(content: str) -> dict:
    """Wrap text in a chat-completions response envelope."""
    return {"choices": [{"message": {"content": content}}]}


def _read_dotenv_key(name: str) -> str:
    """Read a key from the repo .env file (conftest blanks live env keys)."""
    dotenv = Path(__file__).resolve().parent.parent / ".env"
    if not dotenv.exists():
        return ""
    for line in dotenv.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1].strip()
    return ""


def test_extract_json_object_tolerates_fences_and_prose() -> None:
    """JSON extraction strips fences and surrounding prose."""
    assert extract_json_object('{"a": 1}') == {"a": 1}
    assert extract_json_object('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json_object('Here is the plan: {"a": 1} done.') == {"a": 1}
    with pytest.raises(LiveModelError, match="no JSON object"):
        extract_json_object("no braces here")
    with pytest.raises(LiveModelError, match="not valid JSON"):
        extract_json_object("{not json}")


def _patch_client(monkeypatch: pytest.MonkeyPatch, bodies: list[dict]) -> list[dict]:
    """Replay chat responses and capture request payloads."""
    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        seen.append(json.loads(request.content.decode("utf-8")))
        if isinstance(bodies[0], Exception):
            raise bodies.pop(0)
        return httpx.Response(200, json=bodies.pop(0))

    real_client = httpx.Client
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: real_client(transport=transport, **kwargs)
    )
    return seen


def test_live_planner_parses_valid_dag(monkeypatch: pytest.MonkeyPatch) -> None:
    """A valid JSON reply becomes a schema-validated StepDAG."""
    seen = _patch_client(monkeypatch, [_chat_response(json.dumps(_DAG))])
    planner = MuseSparkPlanner()
    dag = planner._call_live_planner_api(
        "live", "Click login.", _mask_set(), Image.new("RGB", (64, 64)), None
    )
    assert dag.steps[0].target_mask_id == 1
    assert seen[0]["model"] == "muse-spark-1.3"
    assert seen[0]["response_format"] == {"type": "json_object"}
    assert seen[0]["max_tokens"] >= 256


def test_live_planner_retries_once_on_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Garbage first reply triggers one repair retry, then succeeds."""
    seen = _patch_client(
        monkeypatch,
        [_chat_response("oops no json"), _chat_response(json.dumps(_DAG))],
    )
    planner = MuseSparkPlanner()
    dag = planner._call_live_planner_api(
        "live", "Click login.", _mask_set(), Image.new("RGB", (64, 64)), None
    )
    assert dag.plan_summary == "Click login"
    assert len(seen) == 2
    assert "ONLY the JSON object" in seen[1]["messages"][-1]["content"]


def test_live_planner_raises_after_double_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two invalid replies raise LiveModelError instead of mocking."""
    _patch_client(monkeypatch, [_chat_response("oops"), _chat_response("still oops")])
    planner = MuseSparkPlanner()
    with pytest.raises(LiveModelError, match="valid StepDAG"):
        planner._call_live_planner_api(
            "live", "Click login.", _mask_set(), Image.new("RGB", (64, 64)), None
        )


def test_live_planner_rejects_transport_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HTTP failures raise LiveModelError with the status code."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="overloaded")

    real_client = httpx.Client
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: real_client(transport=transport, **kwargs)
    )
    planner = MuseSparkPlanner()
    with pytest.raises(LiveModelError, match="HTTP 500"):
        planner._call_live_planner_api(
            "live", "Click login.", _mask_set(), Image.new("RGB", (64, 64)), None
        )


@pytest.mark.skipif(
    not os.environ.get("MUSEPILOT_LIVE_TESTS"), reason="Live API test (costs credits)"
)
def test_live_planner_wire_emits_valid_dag() -> None:
    """Live: Muse Spark plans over real mask IDs with zero coordinates."""
    from musepilot.config import MusePilotSettings

    key = _read_dotenv_key("MUSEPILOT_META_API_KEY")
    assert key, "MUSEPILOT_META_API_KEY required for live tests"
    settings = MusePilotSettings(execution_mode="live", meta_api_key=key)
    planner = MuseSparkPlanner()
    planner.settings = settings
    dag = planner.plan_workflow(
        workflow_id="live",
        intent="Click the first control.",
        mask_set=_mask_set(),
        som_image=Image.new("RGB", (800, 600), color=(15, 23, 42)),
        trace_id="live-test",
    )
    assert len(dag.steps) >= 1
    assert all(s.target_mask_id in (1, 2) for s in dag.steps)
