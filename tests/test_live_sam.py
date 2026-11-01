# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Focused tests for live SAM 3.1 parsing, dedup, and transport behavior."""

from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
import pytest
from PIL import Image

from musepilot.contracts.schemas import LiveModelError
from musepilot.perception.capture import CapturedFrame
from musepilot.perception.sam_client import (
    SAM31PerceptionClient,
    accumulate_output_text,
    bounding_box_iou,
    dedupe_detections,
    frame_to_png_bytes,
    raster_centroid_in_box,
)
from musepilot.perception.sam_client import (
    _Detection as Detection,
)

FIXTURE = Path(__file__).parent / "fixtures" / "sam_button_record.txt"


def test_bounding_box_iou_scores_overlap() -> None:
    """IoU is 1.0 for identical boxes and 0.0 for disjoint boxes."""
    assert bounding_box_iou((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0
    assert bounding_box_iou((0, 0, 10, 10), (20, 20, 30, 30)) == 0.0
    assert bounding_box_iou((0, 0, 10, 10), (5, 0, 15, 10)) == pytest.approx(1 / 3)


def test_dedupe_keeps_higher_confidence_and_sorts() -> None:
    """Overlapping cross-concept detections merge; survivors sort top-to-bottom."""
    low = Detection("icon", (0, 100, 10, 110), 0.80, None, 0, 0)
    high = Detection("button", (0, 100, 10, 110), 0.95, None, 0, 0)
    other = Detection("button", (50, 10, 60, 20), 0.90, None, 0, 0)
    merged = dedupe_detections([low, high, other])
    assert [d.concept for d in merged] == ["button", "button"]
    assert merged[0].bbox == (50, 10, 60, 20)
    assert merged[1].confidence == 0.95


def test_raster_centroid_uses_mask_moments_with_box_fallback() -> None:
    """Centroid follows set mask pixels; empty rasters fall back to the box."""
    skewed = Detection("button", (0, 0, 10, 10), 0.9, bytes([1, 0, 0, 0]), 2, 2)
    assert raster_centroid_in_box(skewed) == (2, 2)
    empty = Detection("button", (0, 0, 10, 10), 0.9, bytes([0, 0, 0, 0]), 2, 2)
    assert raster_centroid_in_box(empty) == (5, 5)
    missing = Detection("button", (0, 0, 10, 10), 0.9, None, 0, 0)
    assert raster_centroid_in_box(missing) == (5, 5)


def test_accumulate_output_text_joins_deltas_only() -> None:
    """SSE accumulation skips control lines, [DONE], and malformed payloads."""
    lines = [
        "event: response.created",
        'data: {"type": "response.created"}',
        'data: {"type": "response.output_text.delta", "delta": "<0f>0"}',
        "data: not-json",
        'data: {"type": "response.output_text.delta", "delta": "<|box|>"}',
        "data: [DONE]",
    ]
    assert accumulate_output_text(lines) == "<0f>0<|box|>"


def test_downscale_caps_longest_edge() -> None:
    """Large frames shrink to the API cap; small frames pass through at 1.0."""
    small = Image.new("RGB", (800, 600))
    img, scale = SAM31PerceptionClient._downscale_for_api(small)
    assert scale == 1.0 and img.size == (800, 600)
    large = Image.new("RGB", (3200, 1600))
    img, scale = SAM31PerceptionClient._downscale_for_api(large)
    assert max(img.size) == 1600
    assert frame_to_png_bytes(img)[:8] == b"\x89PNG\r\n\x1a\n"


def _sse_transport(body_text: str, status_code: int = 200) -> httpx.MockTransport:
    """Replay one recorded SAM output lane as SSE delta events."""
    chunks = [body_text[i : i + 37] for i in range(0, len(body_text), 37)]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/responses"
        assert "Bearer" in request.headers["Authorization"]
        lines = "".join(
            f"data: {json.dumps({'type': 'response.output_text.delta', 'delta': c, 'item_id': 'msg_test', 'output_index': 0, 'content_index': 0})}\n\n"
            for c in chunks
        )
        lines += (
            f"data: {json.dumps({'type': 'response.output_text.done', 'text': body_text, 'item_id': 'msg_test', 'output_index': 0, 'content_index': 0})}\n\n"
            'data: {"type": "response.completed"}\n\ndata: [DONE]\n\n'
        )
        return httpx.Response(
            status_code, headers={"Content-Type": "text/event-stream"}, text=lines
        )

    return httpx.MockTransport(handler)


def _patch_transport(monkeypatch: pytest.MonkeyPatch, transport: httpx.MockTransport) -> None:
    """Route httpx.Client through a mock transport without patch recursion."""
    real_client = httpx.Client
    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: real_client(transport=transport, **kwargs)
    )


def test_segment_concept_parses_recorded_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    """A recorded SAM lane parses to a detection with decoded mask geometry."""
    transport = _sse_transport(FIXTURE.read_text())
    _patch_transport(monkeypatch, transport)
    client = SAM31PerceptionClient()
    detections = client._segment_concept("e30=", "button", 1.0, "test")
    assert len(detections) == 1
    det = detections[0]
    assert det.concept == "button"
    assert det.bbox == (753, 34, 845, 64)
    assert det.raster is not None and len(det.raster) == det.raster_width * det.raster_height
    assert det.raster_width == 93 and det.raster_height == 31
    centroid = raster_centroid_in_box(det)
    assert 753 <= centroid[0] <= 845 and 34 <= centroid[1] <= 64


def test_segment_concept_rejects_transport_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP failures raise LiveModelError instead of silently mocking."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="overloaded")

    _patch_transport(monkeypatch, httpx.MockTransport(handler))
    client = SAM31PerceptionClient()
    with pytest.raises(LiveModelError, match="HTTP 500"):
        client._segment_concept("e30=", "button", 1.0, "test")


def test_live_segment_frame_raises_honestly_without_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Zero matches across concepts raises LiveModelError with the concept list."""
    monkeypatch.setattr(
        "musepilot.perception.sam_client.SAM31PerceptionClient._segment_concept",
        lambda self, *a, **k: [],
    )
    frame = CapturedFrame(
        image=Image.new("RGB", (64, 64)),
        screen_hash="abc",
        width_px=64,
        height_px=64,
        dpi_scale=1.0,
        state_label="test",
    )
    client = SAM31PerceptionClient()
    with pytest.raises(LiveModelError, match="zero UI controls"):
        client._call_live_sam_api(frame, "live", "test")


@pytest.mark.skipif(
    not os.environ.get("MUSEPILOT_LIVE_TESTS"), reason="Live API test (costs credits)"
)
def test_live_sam_wire_proves_plumbing() -> None:
    """Live: the SAM wire either segments or honestly reports zero matches."""
    from musepilot.config import MusePilotSettings

    dotenv = Path(__file__).resolve().parent.parent / ".env"
    key = ""
    if dotenv.exists():
        for line in dotenv.read_text(encoding="utf-8").splitlines():
            if line.startswith("MUSEPILOT_META_API_KEY="):
                key = line.split("=", 1)[1].strip()
    assert key, "MUSEPILOT_META_API_KEY required for live tests"
    settings = MusePilotSettings(execution_mode="live", meta_api_key=key)
    frame = CapturedFrame(
        image=Image.new("RGB", (64, 64), color=(20, 24, 40)),
        screen_hash="live-probe",
        width_px=64,
        height_px=64,
        dpi_scale=1.0,
        state_label="live-probe",
    )
    client = SAM31PerceptionClient()
    client.settings = settings
    try:
        masks = client._call_live_sam_api(frame, "live", "live-test")
    except LiveModelError as exc:
        assert "zero UI controls" in str(exc)
    else:
        assert len(masks) >= 1
