# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Focused tests for the partner open-weight verifier wire and ROI crops."""

from __future__ import annotations

import json
import os
from pathlib import Path

import httpx
import pytest
from PIL import Image, ImageDraw

from musepilot.contracts.schemas import (
    ActionOp,
    LiveModelError,
    MaskMetadata,
    StepNode,
)
from musepilot.perception.capture import CapturedFrame, compute_image_hash
from musepilot.verification.spark_open_verifier import (
    SparkOpenVerifier,
    crop_roi,
)


def _frame(color: tuple[int, int, int], size: tuple[int, int] = (200, 200)) -> CapturedFrame:
    """Build a solid-color captured frame."""
    image = Image.new("RGB", size, color=color)
    return CapturedFrame(
        image=image,
        screen_hash=compute_image_hash(image),
        width_px=size[0],
        height_px=size[1],
        dpi_scale=1.0,
        state_label="test",
    )


def _step() -> StepNode:
    """Build a click step against mask 1."""
    return StepNode(
        step_id=1,
        operation=ActionOp.CLICK,
        target_mask_id=1,
        expected_outcome="Button shows pressed state",
        reasoning="Mask 1 is the button.",
    )


def _mask(bbox: tuple[int, int, int, int] = (50, 50, 150, 150)) -> MaskMetadata:
    """Build a mask centered on the test frame."""
    return MaskMetadata(
        mask_id=1, bbox=bbox, centroid_px=(100, 100), area_px=10000, confidence=0.95
    )


def test_crop_roi_clamps_and_caps() -> None:
    """ROI crops pad around the box, clamp to frame edges, and cap size."""
    frame = _frame((10, 10, 10), size=(100, 100))
    edge = crop_roi(frame, (80, 80, 120, 120))
    assert edge.size[0] <= 100 and edge.size[1] <= 100
    big = _frame((10, 10, 10), size=(2000, 2000))
    capped = crop_roi(big, (500, 500, 1500, 1500))
    assert max(capped.size) == 512


def _patch_verdicts(monkeypatch: pytest.MonkeyPatch, bodies: list[dict]) -> list[dict]:
    """Replay verdict completions and capture request payloads."""
    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content.decode("utf-8")))
        return httpx.Response(200, json=bodies.pop(0))

    real_client = httpx.Client
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: real_client(transport=transport, **kwargs)
    )
    return seen


def _verdict_body(**overrides: object) -> dict:
    """Wrap a verdict dict in a chat-completions envelope."""
    verdict = {
        "passed": True,
        "confidence": 0.93,
        "observed_change": "Button shows pressed state",
        "obstruction_detected": False,
        "retry_hint": None,
    }
    verdict.update(overrides)
    return {"choices": [{"message": {"content": json.dumps(verdict)}}]}


def test_partner_verifier_sends_roi_pair_and_parses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The verifier POSTs pre/post ROI crops and validates the verdict."""
    seen = _patch_verdicts(monkeypatch, [_verdict_body()])
    verdict = SparkOpenVerifier()._call_live_verifier_api(
        _step(),
        _mask(),
        0.42,
        _frame((0, 0, 0)),
        _frame((255, 255, 255)),
        ("https://partner.test/v1", "key", "meta-models/muse-spark-open-1026", "baseten"),
    )
    assert verdict.passed is True
    assert verdict.confidence == 0.93
    assert verdict.roi_pixel_delta == 0.42
    payload = seen[0]
    assert payload["model"] == "meta-models/muse-spark-open-1026"
    assert payload["response_format"] == {"type": "json_object"}
    parts = payload["messages"][1]["content"]
    assert sum(1 for p in parts if p.get("type") == "image_url") == 2


def test_partner_verifier_retries_once_on_garbage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An invalid first reply triggers one repair retry."""
    seen = _patch_verdicts(
        monkeypatch,
        [
            {"choices": [{"message": {"content": "oops"}}]},
            _verdict_body(passed=False, retry_hint="Retry the click."),
        ],
    )
    verdict = SparkOpenVerifier()._call_live_verifier_api(
        _step(),
        _mask(),
        0.01,
        _frame((0, 0, 0)),
        _frame((0, 0, 0)),
        ("https://partner.test/v1", "key", "meta-models/muse-spark-open-1026", "baseten"),
    )
    assert verdict.passed is False
    assert verdict.retry_hint == "Retry the click."
    assert len(seen) == 2


def test_partner_verifier_raises_after_double_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two invalid replies raise LiveModelError instead of mocking."""
    _patch_verdicts(
        monkeypatch,
        [
            {"choices": [{"message": {"content": "oops"}}]},
            {"choices": [{"message": {"content": "still oops"}}]},
        ],
    )
    with pytest.raises(LiveModelError, match="valid verdict"):
        SparkOpenVerifier()._call_live_verifier_api(
            _step(),
            _mask(),
            0.01,
            _frame((0, 0, 0)),
            _frame((0, 0, 0)),
            ("https://partner.test/v1", "key", "meta-models/muse-spark-open-1026", "baseten"),
        )


def test_partner_verifier_rejects_transport_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """HTTP failures raise LiveModelError with the status code."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="bad key")

    real_client = httpx.Client
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: real_client(transport=transport, **kwargs)
    )
    with pytest.raises(LiveModelError, match="HTTP 401"):
        SparkOpenVerifier()._call_live_verifier_api(
            _step(),
            _mask(),
            0.42,
            _frame((0, 0, 0)),
            _frame((255, 255, 255)),
            ("https://partner.test/v1", "key", "meta-models/muse-spark-open-1026", "baseten"),
        )


def _read_dotenv_key(name: str) -> str:
    """Read a key from the repo .env file (conftest blanks live env keys)."""
    dotenv = Path(__file__).resolve().parent.parent / ".env"
    if not dotenv.exists():
        return ""
    for line in dotenv.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{name}=") and "your_partner" not in line:
            return line.split("=", 1)[1].strip()
    return ""


def test_live_credentials_follow_backend_switch() -> None:
    """Credential resolution honors verifier_backend and missing keys."""
    from musepilot.config import MusePilotSettings

    meta = SparkOpenVerifier()
    meta.settings = MusePilotSettings(
        verifier_backend="meta", meta_api_key="meta-key", partner_api_key=""
    )
    base_url, key, model_id, provider = meta._live_credentials() or ("", "", "", "")
    assert base_url == "https://api.meta.ai/v1"
    assert key == "meta-key"
    assert model_id == "muse-spark-1.3"
    assert provider == "meta"

    partner = SparkOpenVerifier()
    partner.settings = MusePilotSettings(verifier_backend="partner", partner_api_key="partner-key")
    creds = partner._live_credentials()
    assert creds is not None and creds[3] == "baseten"

    missing = SparkOpenVerifier()
    missing.settings = MusePilotSettings(
        verifier_backend="partner", partner_api_key="", meta_api_key=""
    )
    assert missing._live_credentials() is None

    meta_missing = SparkOpenVerifier()
    meta_missing.settings = MusePilotSettings(
        verifier_backend="meta", meta_api_key="", partner_api_key="partner-key"
    )
    assert meta_missing._live_credentials() is None


def test_verifier_backend_rejects_unknown_values() -> None:
    """Invalid backend values fail closed at settings validation."""
    import pydantic

    from musepilot.config import MusePilotSettings

    with pytest.raises(pydantic.ValidationError):
        MusePilotSettings(verifier_backend="anthropic")


@pytest.mark.skipif(
    not os.environ.get("MUSEPILOT_LIVE_TESTS"),
    reason="Live API test (costs credits)",
)
def test_live_meta_verifier_judges_real_transition() -> None:
    """Live: the Meta-backend verifier judges a genuine pre/post ROI change."""
    from musepilot.config import MusePilotSettings

    key = _read_dotenv_key("MUSEPILOT_META_API_KEY")
    assert key, "MUSEPILOT_META_API_KEY required for live tests"
    settings = MusePilotSettings(execution_mode="live", verifier_backend="meta", meta_api_key=key)
    pre_image = Image.new("RGB", (200, 200), color=(30, 30, 30))
    post_image = Image.new("RGB", (200, 200), color=(30, 30, 30))
    ImageDraw.Draw(post_image).rectangle([50, 50, 150, 150], fill=(0, 255, 136))
    pre = CapturedFrame(
        image=pre_image,
        screen_hash=compute_image_hash(pre_image),
        width_px=200,
        height_px=200,
        dpi_scale=1.0,
        state_label="live-pre",
    )
    post = CapturedFrame(
        image=post_image,
        screen_hash=compute_image_hash(post_image),
        width_px=200,
        height_px=200,
        dpi_scale=1.0,
        state_label="live-post",
    )
    verifier = SparkOpenVerifier()
    verifier.settings = settings
    verdict = verifier.verify_transition(_step(), _mask(), pre, post, trace_id="live-test")
    assert verdict.model_id == "muse-spark-1.3"
    assert verdict.partner_provider == "meta"
    assert isinstance(verdict.passed, bool)
    assert verdict.roi_pixel_delta > 0.0


@pytest.mark.skipif(
    not os.environ.get("MUSEPILOT_LIVE_TESTS") or not _read_dotenv_key("MUSEPILOT_PARTNER_API_KEY"),
    reason="Needs MUSEPILOT_LIVE_TESTS and a partner API key",
)
def test_live_partner_verifier_judges_real_transition() -> None:
    """Live: the open-weight verifier judges a genuine pre/post ROI change."""
    from musepilot.config import MusePilotSettings

    settings = MusePilotSettings(
        execution_mode="live", partner_api_key=_read_dotenv_key("MUSEPILOT_PARTNER_API_KEY")
    )
    pre_image = Image.new("RGB", (200, 200), color=(30, 30, 30))
    post_image = Image.new("RGB", (200, 200), color=(30, 30, 30))
    ImageDraw.Draw(post_image).rectangle([50, 50, 150, 150], fill=(0, 255, 136))
    pre = CapturedFrame(
        image=pre_image,
        screen_hash=compute_image_hash(pre_image),
        width_px=200,
        height_px=200,
        dpi_scale=1.0,
        state_label="live-pre",
    )
    post = CapturedFrame(
        image=post_image,
        screen_hash=compute_image_hash(post_image),
        width_px=200,
        height_px=200,
        dpi_scale=1.0,
        state_label="live-post",
    )
    verifier = SparkOpenVerifier()
    verifier.settings = settings
    verdict = verifier.verify_transition(_step(), _mask(), pre, post, trace_id="live-test")
    assert isinstance(verdict.passed, bool)
    assert 0.0 <= verdict.confidence <= 1.0
    assert verdict.roi_pixel_delta > 0.0
