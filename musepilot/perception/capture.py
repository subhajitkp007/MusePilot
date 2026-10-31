# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Screen capture and deterministic canvas rendering with SHA-256 frame hashing."""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass

from PIL import Image, ImageDraw

from musepilot.config import get_settings


@dataclass(frozen=True)
class CapturedFrame:
    """Represents a captured RGB frame and its deterministic SHA-256 screen hash."""

    image: Image.Image
    screen_hash: str
    width_px: int
    height_px: int
    dpi_scale: float
    state_label: str = "initial"

    def to_png_bytes(self) -> bytes:
        buf = io.BytesIO()
        self.image.save(buf, format="PNG")
        return buf.getvalue()


def compute_image_hash(image: Image.Image) -> str:
    """Compute a deterministic SHA-256 hex digest over raw RGB frame bytes."""
    rgb = image.convert("RGB")
    return hashlib.sha256(rgb.tobytes()).hexdigest()[:16]


class ScreenCaptureEngine:
    """Captures OS screen frames or renders deterministic canvas states for W1/W2."""

    def __init__(self, dpi_scale: float | None = None) -> None:
        settings = get_settings()
        self.dpi_scale = dpi_scale or settings.display_dpi_scale

    def render_canvas_state(
        self,
        workflow_id: str,
        state_label: str = "initial",
        width_px: int = 1280,
        height_px: int = 800,
    ) -> CapturedFrame:
        """Render a high-contrast synthetic HTML5 Canvas UI state for W1 or W2."""
        img = Image.new("RGB", (width_px, height_px), color=(15, 20, 32))
        draw = ImageDraw.Draw(img)

        # Header bar
        draw.rectangle([0, 0, width_px, 64], fill=(24, 34, 56))
        draw.text(
            (28, 22),
            f"MUSEPILOT TARGET CANVAS // WORKFLOW: {workflow_id.upper()} // STATE: {state_label.upper()}",
            fill=(140, 220, 255),
        )

        if workflow_id.lower() == "w1":
            self._draw_w1_canvas(draw, state_label)
        else:
            self._draw_w2_canvas(draw, state_label)

        frame_hash = compute_image_hash(img)
        return CapturedFrame(
            image=img,
            screen_hash=frame_hash,
            width_px=width_px,
            height_px=height_px,
            dpi_scale=self.dpi_scale,
            state_label=state_label,
        )

    def _draw_w1_canvas(self, draw: ImageDraw.ImageDraw, state_label: str) -> None:
        """Draw Workflow 1: WebGL/HTML5 Engineering Simulation Calibration Canvas."""
        # Mask 1: Frequency Slider Track & Handle (120, 160, 520, 220)
        slider_fill = (
            (0, 210, 150)
            if "step_1" in state_label or "step_2" in state_label or "final" in state_label
            else (60, 90, 140)
        )
        draw.rectangle([120, 160, 520, 220], fill=(28, 40, 65), outline=slider_fill, width=3)
        knob_x = (
            420
            if ("step_1" in state_label or "step_2" in state_label or "final" in state_label)
            else 220
        )
        draw.rectangle([knob_x - 20, 165, knob_x + 20, 215], fill=slider_fill)
        draw.text((135, 135), "FREQUENCY SLIDER (75% TARGET)", fill=(200, 220, 240))

        # Mask 2: Adaptive Damping Toggle Switch (120, 290, 380, 360)
        damping_on = "step_2" in state_label or "final" in state_label
        toggle_color = (0, 220, 130) if damping_on else (75, 85, 110)
        draw.rectangle([120, 290, 380, 360], fill=toggle_color, outline=(200, 240, 255), width=2)
        draw.text(
            (145, 318),
            f"ADAPTIVE DAMPING: {'ENABLED' if damping_on else 'OFF'}",
            fill=(15, 20, 32) if damping_on else (230, 235, 245),
        )

        # Mask 3: Parameter Gain Input Field (120, 420, 520, 490)
        gain_filled = "step_3" in state_label or "final" in state_label
        draw.rectangle(
            [120, 420, 520, 490],
            fill=(22, 30, 48),
            outline=(0, 200, 255) if gain_filled else (90, 110, 145),
            width=3,
        )
        draw.text(
            (140, 448),
            "GAIN_COEFF: 0.942 [LOCKED]" if gain_filled else "GAIN_COEFF: <enter value>",
            fill=(120, 255, 190) if gain_filled else (150, 165, 190),
        )

        # Mask 4: Execute Simulation Benchmark Button (120, 560, 440, 640)
        completed = "final" in state_label
        btn_fill = (16, 185, 129) if completed else (59, 130, 246)
        draw.rectangle([120, 560, 440, 640], fill=btn_fill, outline=(255, 255, 255), width=2)
        draw.text(
            (155, 592),
            "BENCHMARK VERIFIED [OK]" if completed else "RUN BENCHMARK SIMULATION",
            fill=(255, 255, 255),
        )

        # Right-hand Telemetry Waveform Canvas Viewport
        draw.rectangle([620, 130, 1200, 660], fill=(10, 16, 26), outline=(50, 80, 120), width=2)
        status_banner = (
            "STATUS: CONVERGED // Q-FACTOR = 99.4%"
            if completed
            else f"STATUS: CALIBRATING ({state_label})"
        )
        draw.text((650, 160), status_banner, fill=(52, 211, 153) if completed else (250, 204, 21))

        # Draw synthetic waveform bars inside viewport
        for idx in range(12):
            bar_x = 660 + idx * 42
            bar_h = (120 + (idx * 23) % 180) if completed else (60 + (idx * 17) % 90)
            draw.rectangle(
                [bar_x, 580 - bar_h, bar_x + 26, 580],
                fill=(16, 185, 129) if completed else (56, 189, 248),
            )

    def _draw_w2_canvas(self, draw: ImageDraw.ImageDraw, state_label: str) -> None:
        """Draw Workflow 2: Cross-App Anomaly Telemetry & Incident Dispatch Portal."""
        # Mask 1: Extract Anomaly Snapshot Button (100, 150, 460, 225)
        extracted = state_label != "initial"
        draw.rectangle(
            [100, 150, 460, 225],
            fill=(14, 165, 233) if not extracted else (16, 185, 129),
            outline=(255, 255, 255),
            width=2,
        )
        draw.text(
            (130, 180),
            "ANOMALY SNAPSHOT COPIED" if extracted else "1. EXTRACT ANOMALY METRICS",
            fill=(255, 255, 255),
        )

        # Mask 2: Incident Summary Input Box (100, 285, 620, 375)
        typed = "step_2" in state_label or "final" in state_label
        draw.rectangle(
            [100, 285, 620, 375],
            fill=(24, 34, 54),
            outline=(52, 211, 153) if typed else (100, 116, 139),
            width=3,
        )
        draw.text(
            (125, 322),
            "INCIDENT: GPU-NODE-07 LATENCY SPIKE (+42ms)"
            if typed
            else "INCIDENT REPORT SUMMARY...",
            fill=(167, 243, 208) if typed else (148, 163, 184),
        )

        # Mask 3: Dispatch Alert Button (100, 435, 460, 515)
        dispatched = "final" in state_label
        draw.rectangle(
            [100, 435, 460, 515],
            fill=(16, 185, 129) if dispatched else (245, 158, 11),
            outline=(255, 255, 255),
            width=2,
        )
        draw.text(
            (135, 468),
            "INCIDENT DISPATCHED [ACK]" if dispatched else "3. DISPATCH URGENT ALERT",
            fill=(255, 255, 255),
        )

        # If modal obstruction is active (Self-healing showcase!)
        if "modal" in state_label:
            draw.rectangle(
                [320, 200, 960, 560],
                fill=(45, 18, 30),
                outline=(244, 63, 94),
                width=4,
            )
            draw.text(
                (370, 250),
                "WARNING: TRANSIENT SESSION SYNC MODAL BLOCKING UI",
                fill=(253, 164, 175),
            )
            # Mask 4: Dismiss Modal Button (500, 420, 780, 495)
            draw.rectangle(
                [500, 420, 780, 495],
                fill=(225, 29, 72),
                outline=(255, 255, 255),
                width=2,
            )
            draw.text((545, 450), "DISMISS & RESYNC [MASK #4]", fill=(255, 255, 255))
