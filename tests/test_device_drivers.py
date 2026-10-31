# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Unit tests for pluggable device drivers and driver factory."""

from __future__ import annotations

from unittest.mock import MagicMock

from PIL import Image

from musepilot.execution.device import (
    AdbDeviceDriver,
    DesktopDeviceDriver,
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

    # Input dispatch calls execute safely without crashing
    driver.tap(100.0, 200.0)
    driver.swipe(100.0, 100.0, 200.0, 200.0, duration_ms=250)
    driver.text("hello world")


def test_device_driver_factory() -> None:
    assert get_device_driver("simulated") is None
    desktop = get_device_driver("desktop")
    assert isinstance(desktop, DesktopDeviceDriver)


def test_adb_driver_mocked(monkeypatch) -> None:
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
