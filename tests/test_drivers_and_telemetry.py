# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Focused tests for drag vectors, telemetry gating/export, and mobile drivers."""

from __future__ import annotations

import subprocess
from typing import Any

import pytest
from PIL import Image

from musepilot.config import get_settings
from musepilot.contracts.schemas import ActionOp, StepNode
from musepilot.execution import ActionExecutor
from musepilot.execution.device import AdbDeviceDriver, DeviceDriver
from musepilot.perception import (
    SAM31PerceptionClient,
    ScreenCaptureEngine,
    compute_image_hash,
)
from musepilot.perception.capture import CapturedFrame
from musepilot.telemetry import GLOBAL_TELEMETRY


class FakeDeviceDriver(DeviceDriver):
    """In-memory device driver recording dispatch calls for tests."""

    def __init__(self, frame_image: Image.Image) -> None:
        self._frame_image = frame_image
        self.calls: list[tuple[str, Any]] = []

    @property
    def serial(self) -> str:
        return "fake-device-001"

    def is_available(self) -> bool:
        return True

    def tap(self, x: float, y: float) -> None:
        self.calls.append(("tap", (x, y)))

    def swipe(self, x1: float, y1: float, x2: float, y2: float, duration_ms: int = 300) -> None:
        self.calls.append(("swipe", (x1, y1, x2, y2, duration_ms)))

    def text(self, value: str) -> None:
        self.calls.append(("text", value))

    def capture_frame(self, state_label: str = "initial") -> CapturedFrame:
        width, height = self._frame_image.size
        return CapturedFrame(
            image=self._frame_image,
            screen_hash=compute_image_hash(self._frame_image),
            width_px=width,
            height_px=height,
            dpi_scale=get_settings().display_dpi_scale,
            state_label=state_label,
        )


def _w1_mask_setup() -> Any:
    capture = ScreenCaptureEngine(dpi_scale=2.0)
    frame = capture.render_canvas_state(workflow_id="w1", state_label="initial")
    mask_set = SAM31PerceptionClient().segment_frame(frame, workflow_id="w1")
    return capture, frame, mask_set


def test_drag_step_records_destination_vector() -> None:
    """Prove drag steps resolve the destination mask into the receipt."""
    capture, pre_frame, mask_set = _w1_mask_setup()
    step = StepNode(
        step_id=1,
        operation=ActionOp.DRAG,
        target_mask_id=1,
        drag_to_mask_id=2,
        expected_outcome="Slider handle drags toward the damping toggle",
    )
    _, receipt = ActionExecutor(capture).execute_step(
        workflow_id="w1",
        step=step,
        mask_set=mask_set,
        pre_frame=pre_frame,
        next_state_label="step_1",
    )

    assert receipt.drag_to_logical_point is not None
    assert receipt.drag_to_logical_point != receipt.os_logical_point


def test_non_drag_receipt_has_no_destination_vector() -> None:
    """Prove click receipts leave the drag destination empty."""
    capture, pre_frame, mask_set = _w1_mask_setup()
    step = StepNode(
        step_id=1,
        operation=ActionOp.CLICK,
        target_mask_id=1,
        expected_outcome="Slider activates",
    )
    _, receipt = ActionExecutor(capture).execute_step(
        workflow_id="w1",
        step=step,
        mask_set=mask_set,
        pre_frame=pre_frame,
        next_state_label="step_1",
    )

    assert receipt.drag_to_logical_point is None


def test_telemetry_disabled_records_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prove telemetry_enabled=false suppresses spans and latency samples."""
    monkeypatch.setenv("MUSEPILOT_TELEMETRY_ENABLED", "false")
    GLOBAL_TELEMETRY.reset()
    try:
        with GLOBAL_TELEMETRY.start_span("test.gated", trace_id="t1"):
            GLOBAL_TELEMETRY.record_sam_latency(9.9)
        assert GLOBAL_TELEMETRY.spans == []
        assert GLOBAL_TELEMETRY.median_sam_ms == 0.0
    finally:
        GLOBAL_TELEMETRY.reset()


def test_otlp_payload_shape() -> None:
    """Prove the OTLP/HTTP payload carries resource spans with nano timestamps."""
    GLOBAL_TELEMETRY.reset()
    try:
        with GLOBAL_TELEMETRY.start_span(
            "test.otlp", trace_id="abc123", model_id="meta-models/sam-3.1"
        ):
            pass
        payload = GLOBAL_TELEMETRY.to_otlp_payload()
        spans = payload["resourceSpans"][0]["scopeSpans"][0]["spans"]
        assert len(spans) == 1
        assert spans[0]["name"] == "test.otlp"
        assert len(spans[0]["traceId"]) == 32
        assert len(spans[0]["spanId"]) == 16
        assert isinstance(spans[0]["startTimeUnixNano"], str)
    finally:
        GLOBAL_TELEMETRY.reset()


def test_otlp_export_fails_soft_without_collector() -> None:
    """Prove export returns False instead of raising when no collector listens."""
    GLOBAL_TELEMETRY.reset()
    try:
        with GLOBAL_TELEMETRY.start_span("test.export", trace_id="t1"):
            pass
        assert GLOBAL_TELEMETRY.export_otlp("http://127.0.0.1:1/v1/traces") is False
    finally:
        GLOBAL_TELEMETRY.reset()


def test_adb_driver_availability_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prove availability follows the adb binary discovery."""
    monkeypatch.setattr("musepilot.execution.device._find_adb", lambda: None)
    assert AdbDeviceDriver.is_available() is False
    monkeypatch.setattr("musepilot.execution.device._find_adb", lambda: "/usr/bin/adb")
    assert AdbDeviceDriver.is_available() is True


def test_adb_driver_lists_devices(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prove device-list parsing returns attached serials."""
    completed = subprocess.CompletedProcess(
        args=["adb", "devices"],
        returncode=0,
        stdout="List of devices attached\nemulator-5554\tdevice product:sdk\n",
        stderr="",
    )
    monkeypatch.setattr("subprocess.run", lambda *a, **k: completed)
    monkeypatch.setattr("shutil.which", lambda _name: "/usr/bin/adb")
    assert AdbDeviceDriver.list_devices() == ["emulator-5554"]


def test_adb_driver_tap_command_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prove taps dispatch the exact adb input command for the serial."""
    seen: dict[str, Any] = {}

    def fake_run(cmd: Any, **kwargs: Any) -> Any:
        seen["cmd"] = list(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)
    monkeypatch.setattr("shutil.which", lambda _name: "/usr/bin/adb")
    monkeypatch.setenv("MUSEPILOT_ALLOW_LIVE_INPUT", "true")
    AdbDeviceDriver(serial="emulator-5554").tap(320.0, 200.0)

    assert seen["cmd"] == [
        "/usr/bin/adb",
        "-s",
        "emulator-5554",
        "shell",
        "input",
        "tap",
        "320",
        "200",
    ]


def test_executor_dispatches_through_device_driver() -> None:
    """Prove execute_step uses an injected driver for dispatch and capture."""
    capture, pre_frame, mask_set = _w1_mask_setup()
    image = Image.new("RGB", (640, 400), color=(10, 10, 10))
    driver = FakeDeviceDriver(image)
    step = StepNode(
        step_id=1,
        operation=ActionOp.CLICK,
        target_mask_id=1,
        expected_outcome="Slider activates via device tap",
    )
    post_frame, receipt = ActionExecutor(capture).execute_step(
        workflow_id="w1",
        step=step,
        mask_set=mask_set,
        pre_frame=pre_frame,
        next_state_label="step_1",
        device_driver=driver,
    )

    assert driver.calls and driver.calls[0][0] == "tap"
    assert post_frame.image.size == (640, 400)
    assert receipt.post_frame_hash == post_frame.screen_hash
    assert receipt.pre_frame_hash == pre_frame.screen_hash
