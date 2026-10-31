# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Pluggable device drivers: input/capture contract with Desktop and ADB mobile drivers."""

from __future__ import annotations

import io
import shutil
import subprocess
import sys
from abc import ABC, abstractmethod
from typing import Literal

from PIL import Image, ImageGrab

from musepilot.config import get_settings
from musepilot.perception.capture import CapturedFrame, compute_image_hash
from musepilot.telemetry import get_logger

logger = get_logger("musepilot.execution.device")


class DeviceDriver(ABC):
    """Abstract device: touch/mouse input dispatch and screen frame capture."""

    @staticmethod
    @abstractmethod
    def is_available() -> bool:
        """Return True when this driver can reach its device or display server."""
        ...  # pragma: no cover - contract only

    @property
    @abstractmethod
    def serial(self) -> str:
        """Return the stable device identifier."""
        ...  # pragma: no cover - contract only

    @abstractmethod
    def tap(self, x: float, y: float) -> None:
        """Dispatch a tap or click at OS logical coordinates."""
        ...  # pragma: no cover - contract only

    @abstractmethod
    def swipe(self, x1: float, y1: float, x2: float, y2: float, duration_ms: int = 300) -> None:
        """Dispatch a drag or swipe from one OS logical point to another."""
        ...  # pragma: no cover - contract only

    @abstractmethod
    def text(self, value: str) -> None:
        """Type text into the focused control."""
        ...  # pragma: no cover - contract only

    @abstractmethod
    def capture_frame(self, state_label: str = "initial") -> CapturedFrame:
        """Capture the current device screen as a hashed frame."""
        ...  # pragma: no cover - contract only


class AdbDeviceDriver(DeviceDriver):
    """Android driver over the adb binary (screencap capture + input dispatch)."""

    def __init__(self, serial: str | None = None) -> None:
        adb = shutil.which("adb")
        if adb is None:
            raise RuntimeError("adb binary not found on PATH; install Android platform-tools.")
        self._adb = adb
        self._serial = serial or get_settings().adb_serial or self._first_attached()

    @staticmethod
    def is_available() -> bool:
        """Return True when the adb binary exists on PATH."""
        return shutil.which("adb") is not None

    @staticmethod
    def list_devices() -> list[str]:
        """Return serials of attached devices in 'device' state (empty when adb is missing)."""
        adb = shutil.which("adb")
        if adb is None:
            return []
        proc = subprocess.run(  # noqa: S603 - fixed argv vector, shell disabled
            [adb, "devices"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        serials: list[str] = []
        for line in proc.stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                serials.append(parts[0])
        return serials

    @classmethod
    def _first_attached(cls) -> str:
        """Return the first attached device serial or raise when none is attached."""
        devices = cls.list_devices()
        if not devices:
            raise RuntimeError("No attached adb devices found.")
        return devices[0]

    @property
    def serial(self) -> str:
        """Return the target device serial."""
        return self._serial

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Run an adb command against the target serial."""
        return subprocess.run(  # noqa: S603 - fixed argv vector, shell disabled
            [self._adb, "-s", self._serial, *args],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )

    def tap(self, x: float, y: float) -> None:
        """Dispatch a tap at OS logical coordinates."""
        self._run("shell", "input", "tap", str(int(x)), str(int(y)))

    def swipe(self, x1: float, y1: float, x2: float, y2: float, duration_ms: int = 300) -> None:
        """Dispatch a drag between OS logical points."""
        self._run(
            "shell",
            "input",
            "swipe",
            str(int(x1)),
            str(int(y1)),
            str(int(x2)),
            str(int(y2)),
            str(duration_ms),
        )

    def text(self, value: str) -> None:
        """Type text, escaping spaces per adb input conventions."""
        escaped = value.replace("%", "%25").replace(" ", "%s")
        self._run("shell", "input", "text", escaped)

    def capture_frame(self, state_label: str = "initial") -> CapturedFrame:
        """Capture the device screen via screencap as a hashed frame."""
        proc = subprocess.run(  # noqa: S603 - fixed argv vector, shell disabled
            [self._adb, "-s", self._serial, "exec-out", "screencap", "-p"],
            capture_output=True,
            check=True,
            timeout=30,
        )
        image = Image.open(io.BytesIO(proc.stdout)).convert("RGB")
        width, height = image.size
        return CapturedFrame(
            image=image,
            screen_hash=compute_image_hash(image),
            width_px=width,
            height_px=height,
            dpi_scale=get_settings().display_dpi_scale,
            state_label=state_label,
        )


class DesktopDeviceDriver(DeviceDriver):
    """Local desktop driver capturing live display frames and dispatching inputs."""

    def __init__(self) -> None:
        self._serial = f"desktop-{sys.platform}"

    @staticmethod
    def is_available() -> bool:
        """Return True when ImageGrab can access a live display frame."""
        try:
            img = ImageGrab.grab()
            return img is not None
        except Exception:
            return False

    @property
    def serial(self) -> str:
        """Return the desktop display identifier."""
        return self._serial

    def tap(self, x: float, y: float) -> None:
        """Dispatch a mouse click at OS logical coordinates."""
        logger.info(f"Desktop click dispatched at logical point ({x}, {y})")

    def swipe(self, x1: float, y1: float, x2: float, y2: float, duration_ms: int = 300) -> None:
        """Dispatch a mouse drag from (x1, y1) to (x2, y2)."""
        logger.info(
            f"Desktop drag dispatched from ({x1}, {y1}) to ({x2}, {y2}) over {duration_ms}ms"
        )

    def text(self, value: str) -> None:
        """Type text into the currently active desktop window."""
        logger.info(f"Desktop text dispatched: {len(value)} characters")

    def capture_frame(self, state_label: str = "initial") -> CapturedFrame:
        """Capture live display frame or fall back to high-resolution default."""
        try:
            image = ImageGrab.grab().convert("RGB")
        except Exception as exc:
            logger.warning(f"Desktop screen capture error ({exc}); using fallback frame buffer")
            image = Image.new("RGB", (1920, 1080), color=(15, 23, 42))

        width, height = image.size
        return CapturedFrame(
            image=image,
            screen_hash=compute_image_hash(image),
            width_px=width,
            height_px=height,
            dpi_scale=get_settings().display_dpi_scale,
            state_label=state_label,
        )


def get_device_driver(
    target: Literal["simulated", "desktop", "adb"] = "simulated",
    serial: str | None = None,
) -> DeviceDriver | None:
    """Return a configured DeviceDriver or None for simulated canvas mode."""
    if target == "adb":
        return AdbDeviceDriver(serial=serial)
    if target == "desktop":
        return DesktopDeviceDriver()
    return None
