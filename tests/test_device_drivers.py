# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Unit tests for pluggable device drivers and driver factory."""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest
from PIL import Image

from musepilot.execution.device import (
    AdbDeviceDriver,
    DesktopDeviceDriver,
    LiveInputDisabledError,
    get_device_driver,
)


def test_desktop_device_driver_methods(monkeypatch) -> None:
    driver = DesktopDeviceDriver()
    assert "desktop" in driver.serial

    # Mock ImageGrab.grab to return a synthetic PIL image
    mock_img = Image.new("RGB", (800, 600), color=(10, 20, 30))
    monkeypatch.setattr("PIL.ImageGrab.grab", lambda: mock_img)

    assert DesktopDeviceDriver.is_available() is True
    frame = driver.capture_frame(state_label="test")
    assert frame.width_px == 800
    assert frame.height_px == 600
    assert frame.state_label == "test"

    # Dispatch without the opt-in fails closed instead of touching the OS
    with pytest.raises(LiveInputDisabledError):
        driver.tap(100.0, 200.0)
    with pytest.raises(LiveInputDisabledError):
        driver.swipe(100.0, 100.0, 200.0, 200.0, duration_ms=250)
    with pytest.raises(LiveInputDisabledError):
        driver.text("hello world")


def test_desktop_dispatch_drives_os_controllers(monkeypatch) -> None:
    """With the opt-in set, desktop dispatch drives pynput controllers."""
    monkeypatch.setenv("MUSEPILOT_ALLOW_LIVE_INPUT", "true")
    calls: dict = {}

    class FakeMouse:
        left = "left"

        def __init__(self) -> None:
            calls["mouse"] = self

        def click(self, button: object, count: int) -> None:
            calls["click"] = (button, count, self.position)

        def press(self, button: object) -> None:
            calls.setdefault("press_release", []).append(("press", button))

        def release(self, button: object) -> None:
            calls.setdefault("press_release", []).append(("release", button))

    class FakeMouseModule(types.ModuleType):
        Controller = FakeMouse

        class Button:
            left = "left"

    class FakeKeyboard:
        def __init__(self) -> None:
            calls["keyboard"] = self

        def type(self, value: str) -> None:
            calls["typed"] = value

    class FakeKeyboardModule(types.ModuleType):
        Controller = FakeKeyboard

    monkeypatch.setitem(sys.modules, "pynput", types.ModuleType("pynput"))
    monkeypatch.setitem(sys.modules, "pynput.mouse", FakeMouseModule("pynput.mouse"))
    monkeypatch.setitem(sys.modules, "pynput.keyboard", FakeKeyboardModule("pynput.keyboard"))
    monkeypatch.setattr("time.sleep", lambda seconds: None)

    driver = DesktopDeviceDriver()
    driver.tap(100.0, 200.0)
    assert calls["click"][2] == (100.0, 200.0)
    driver.swipe(0.0, 0.0, 10.0, 10.0, duration_ms=32)
    assert calls["press_release"][0][0] == "press"
    assert calls["press_release"][-1][0] == "release"
    driver.text("hello world")
    assert calls["typed"] == "hello world"


def test_desktop_tap_detects_ignored_cursor_move(monkeypatch) -> None:
    """A cursor the OS refuses to move raises instead of clicking blind."""
    import musepilot.execution.device as device_module

    monkeypatch.setenv("MUSEPILOT_ALLOW_LIVE_INPUT", "true")

    class StuckMouse:
        """Simulates macOS ignoring cursor moves without Accessibility consent."""

        def __init__(self) -> None:
            self._pos = (0.0, 0.0)

        @property
        def position(self) -> tuple[float, float]:
            return self._pos

        @position.setter
        def position(self, value: tuple[float, float]) -> None:
            pass

        def click(self, button: object, count: int) -> None:  # pragma: no cover
            raise AssertionError("must not click when the move was ignored")

    class StuckModule(types.ModuleType):
        Controller = StuckMouse

        class Button:
            left = "left"

    monkeypatch.setitem(sys.modules, "pynput", types.ModuleType("pynput"))
    monkeypatch.setitem(sys.modules, "pynput.mouse", StuckModule("pynput.mouse"))
    with pytest.raises(device_module.DeviceDispatchError, match="Accessibility"):
        DesktopDeviceDriver().tap(400.0, 400.0)


def test_device_driver_factory() -> None:
    assert get_device_driver("simulated") is None
    desktop = get_device_driver("desktop")
    assert isinstance(desktop, DesktopDeviceDriver)


def test_adb_driver_mocked(monkeypatch) -> None:
    monkeypatch.setenv("MUSEPILOT_ALLOW_LIVE_INPUT", "true")
    monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/adb" if cmd == "adb" else None)
    mock_run = MagicMock()
    mock_run.return_value.stdout = "List of devices attached\nemulator-5554\tdevice\n"
    monkeypatch.setattr("subprocess.run", mock_run)

    assert AdbDeviceDriver.is_available() is True
    assert AdbDeviceDriver.list_devices() == ["emulator-5554"]

    driver = AdbDeviceDriver(serial="emulator-5554")
    assert driver.serial == "emulator-5554"

    driver.tap(150.0, 300.0)
    assert mock_run.called


def test_orchestrator_accepts_device_driver() -> None:
    from musepilot.orchestrator import MusePilotOrchestrator

    driver = DesktopDeviceDriver()
    orchestrator = MusePilotOrchestrator(device_driver=driver)
    assert orchestrator.device_driver is driver
