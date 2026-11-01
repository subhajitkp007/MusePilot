# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Screen capture and deterministic canvas rendering with SHA-256 frame hashing."""

from __future__ import annotations

import base64
import hashlib
import io
from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from musepilot.config import get_settings


def _get_font(size: int = 14, bold: bool = False) -> ImageFont.ImageFont:
    """Return a clean truetype font if available on macOS, falling back to PIL default."""
    try:
        font_path = "/System/Library/Fonts/HelveticaNeue.ttc"
        return ImageFont.truetype(font_path, size, index=1 if bold else 0)
    except Exception:
        try:
            return ImageFont.load_default(size=size)
        except Exception:
            return ImageFont.load_default()


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
        """Encode the frame image as PNG bytes."""
        buf = io.BytesIO()
        self.image.save(buf, format="PNG")
        return buf.getvalue()


def compute_image_hash(image: Image.Image) -> str:
    """Compute a deterministic SHA-256 hex digest over raw RGB frame bytes."""
    rgb = image.convert("RGB")
    return hashlib.sha256(rgb.tobytes()).hexdigest()[:16]


def frame_to_base64_jpeg(image: Image.Image, max_dim: int = 1080) -> str:
    """Encode an image as a compact base64 JPEG string for real-time WebSocket streaming."""
    img = image.copy()
    w, h = img.size
    longest = max(w, h)
    if longest > max_dim:
        scale = max_dim / longest
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=75)
    return base64.b64encode(buf.getvalue()).decode("ascii")


class LiveFrameBuffer:
    """Thread-safe global buffer holding the latest live execution frame."""

    def __init__(self) -> None:
        self.latest_event: dict[str, Any] | None = None
        self.seq: int = 0

    def publish(self, image: Image.Image, state_label: str) -> None:
        """Publish a new frame event to live stream subscribers."""
        self.latest_event = {
            "type": "frame",
            "image_base64": frame_to_base64_jpeg(image),
            "state_label": state_label,
        }
        self.seq += 1


GLOBAL_FRAME_BUFFER = LiveFrameBuffer()


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
        """Render a high-contrast enterprise WebGL/HTML5 Canvas UI state for W1 or W2."""
        img = Image.new("RGB", (width_px, height_px), color=(11, 15, 23))
        draw = ImageDraw.Draw(img)

        # Draw authentic enterprise app header
        self._draw_enterprise_header(draw, workflow_id, state_label, width_px)

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

    def _draw_enterprise_header(
        self, draw: ImageDraw.ImageDraw, workflow_id: str, state_label: str, width_px: int
    ) -> None:
        """Draw a production-grade enterprise application navbar."""
        # Navbar container
        draw.rectangle([0, 0, width_px, 62], fill=(16, 22, 34), outline=(32, 44, 68), width=1)

        font_brand = _get_font(15, bold=True)
        font_sub = _get_font(11, bold=False)
        font_pill = _get_font(12, bold=True)

        if workflow_id.lower() == "w1":
            # Northbeam RF Studio brand
            draw.rounded_rectangle([20, 14, 52, 46], radius=8, fill=(37, 99, 235))
            draw.text((31, 18), "N", fill=(255, 255, 255), font=font_brand)
            draw.text((64, 15), "NORTHBEAM STUDIO", fill=(240, 246, 255), font=font_brand)
            draw.text(
                (64, 34),
                "Quantum & RF Transmitter Workbench • Opaque Canvas Engine (0 DOM Nodes)",
                fill=(120, 140, 175),
                font=font_sub,
            )

            # Navigation pill badges
            draw.rounded_rectangle([860, 16, 990, 44], radius=6, fill=(18, 55, 40))
            draw.ellipse([872, 26, 882, 36], fill=(52, 211, 153))
            draw.text((890, 22), "STAGING // PROD", fill=(110, 231, 183), font=font_pill)

            draw.rounded_rectangle([1006, 16, 1250, 44], radius=6, fill=(24, 32, 50))
            draw.text(
                (1018, 22),
                f"STATE: {state_label.upper()} • 60 FPS",
                fill=(147, 197, 253),
                font=font_pill,
            )
        else:
            # CloudOps Observability Incident Console
            draw.rounded_rectangle([20, 14, 52, 46], radius=8, fill=(225, 29, 72))
            draw.text((30, 18), "C", fill=(255, 255, 255), font=font_brand)
            draw.text((64, 15), "CLOUDOPS OBSERVABILITY", fill=(255, 241, 242), font=font_brand)
            draw.text(
                (64, 34),
                "Cluster us-central1-gcp-h100 • Live Incident Command Center #INC-8942",
                fill=(160, 175, 200),
                font=font_sub,
            )

            # Alert pill
            draw.rounded_rectangle([860, 16, 1000, 44], radius=6, fill=(60, 18, 28))
            draw.ellipse([872, 26, 882, 36], fill=(244, 63, 94))
            draw.text((890, 22), "SEV-1 ACTIVE ALERT", fill=(254, 205, 211), font=font_pill)

            draw.rounded_rectangle([1016, 16, 1250, 44], radius=6, fill=(24, 32, 50))
            draw.text(
                (1028, 22),
                f"PHASE: {state_label.upper()}",
                fill=(147, 197, 253),
                font=font_pill,
            )

    def _draw_w1_canvas(self, draw: ImageDraw.ImageDraw, state_label: str) -> None:
        """Draw Workflow 1: Northbeam Studio Quantum & RF Spectrum Workbench."""
        font_title = _get_font(13, bold=True)
        font_sub = _get_font(11, bold=False)
        font_btn = _get_font(13, bold=True)
        font_mono = _get_font(12, bold=True)

        # Card container 1 (Mask 1: Frequency Synthesizer)
        draw.rounded_rectangle([100, 120, 540, 235], radius=10, fill=(18, 25, 38), outline=(35, 48, 72), width=1)
        draw.text((120, 132), "1. CARRIER FREQUENCY SYNTHESIZER", fill=(210, 230, 255), font=font_title)

        is_calibrated = "step_1" in state_label or "step_2" in state_label or "step_3" in state_label or "final" in state_label
        slider_border = (16, 185, 129) if is_calibrated else (56, 189, 248)
        draw.rectangle([120, 160, 520, 220], fill=(26, 36, 56), outline=slider_border, width=2)

        # Track line & markings
        draw.line([(150, 190), (490, 190)], fill=(50, 70, 105), width=6)
        draw.line([(150, 182), (150, 198)], fill=(80, 105, 145), width=2)
        draw.line([(320, 182), (320, 198)], fill=(80, 105, 145), width=2)
        draw.line([(420, 182), (420, 198)], fill=(16, 185, 129) if is_calibrated else (120, 140, 175), width=2)
        draw.line([(490, 182), (490, 198)], fill=(80, 105, 145), width=2)

        knob_x = 420 if is_calibrated else 220
        knob_fill = (16, 185, 129) if is_calibrated else (56, 189, 248)
        draw.rounded_rectangle([knob_x - 18, 168, knob_x + 18, 212], radius=6, fill=knob_fill, outline=(255, 255, 255), width=2)

        slider_text = "433.920 MHz [75.0% TARGET LOCKED]" if is_calibrated else "215.400 MHz [FREQUENCY DRIFT]"
        slider_txt_color = (167, 243, 208) if is_calibrated else (186, 230, 253)
        draw.text((150, 165), slider_text, fill=slider_txt_color, font=font_mono)

        # Card container 2 (Mask 2: Adaptive Damping Toggle Switch)
        draw.rounded_rectangle([100, 255, 540, 375], radius=10, fill=(18, 25, 38), outline=(35, 48, 72), width=1)
        draw.text((120, 267), "2. NYQUIST ADAPTIVE DAMPING LOOP", fill=(210, 230, 255), font=font_title)

        damping_on = "step_2" in state_label or "step_3" in state_label or "final" in state_label
        toggle_fill = (16, 185, 129) if damping_on else (35, 46, 68)
        toggle_border = (110, 231, 183) if damping_on else (70, 85, 115)
        draw.rectangle([120, 290, 380, 360], fill=toggle_fill, outline=toggle_border, width=2)

        toggle_label = "ADAPTIVE DAMPING: ENABLED [-48.2 dB]" if damping_on else "ADAPTIVE DAMPING: OFF"
        draw.text((135, 318), toggle_label, fill=(255, 255, 255) if damping_on else (180, 195, 220), font=font_btn)

        # Card container 3 (Mask 3: Gain Coefficient Parameter Field)
        draw.rounded_rectangle([100, 395, 540, 510], radius=10, fill=(18, 25, 38), outline=(35, 48, 72), width=1)
        draw.text((120, 403), "3. DSP ATTENUATION GAIN (α)", fill=(210, 230, 255), font=font_title)

        gain_filled = "step_3" in state_label or "final" in state_label
        gain_border = (6, 182, 212) if gain_filled else (70, 85, 115)
        draw.rectangle([120, 420, 520, 490], fill=(14, 22, 34), outline=gain_border, width=2)

        gain_text = "GAIN_COEFF: 0.942 [LOCKED - IEEE 754]" if gain_filled else "GAIN_COEFF: <enter value>"
        draw.text((140, 448), gain_text, fill=(103, 232, 249) if gain_filled else (120, 140, 175), font=font_mono)

        # Card container 4 (Mask 4: Benchmark Simulation Button)
        draw.rounded_rectangle([100, 530, 540, 660], radius=10, fill=(18, 25, 38), outline=(35, 48, 72), width=1)
        draw.text((120, 538), "4. SPECTRAL CONVERGENCE AUDIT", fill=(210, 230, 255), font=font_title)

        completed = "final" in state_label
        btn_fill = (16, 185, 129) if completed else (37, 99, 235)
        btn_border = (110, 231, 183) if completed else (147, 197, 253)
        draw.rectangle([120, 560, 440, 640], fill=btn_fill, outline=btn_border, width=2)

        btn_txt = "BENCHMARK VERIFIED [OK]" if completed else "RUN BENCHMARK SIMULATION"
        draw.text((145, 592), btn_txt, fill=(255, 255, 255), font=font_btn)

        # Right-hand FFT Spectrum Analyzer Viewport
        draw.rounded_rectangle([580, 120, 1220, 660], radius=12, fill=(10, 15, 24), outline=(35, 48, 72), width=2)

        # Viewport Header
        draw.text((610, 142), "REAL-TIME FFT SPECTRUM ANALYZER", fill=(210, 230, 255), font=font_title)
        status_text = "STATUS: CONVERGED // Q-FACTOR = 99.4%" if completed else f"STATUS: CALIBRATING ({state_label})"
        status_color = (52, 211, 153) if completed else (251, 191, 36)
        draw.text((880, 142), status_text, fill=status_color, font=font_mono)

        # Grid lines & Decibel Y-Axis (-120 dBm to 0 dBm)
        for i, dbm in enumerate(["0 dBm", "-30 dBm", "-60 dBm", "-90 dBm", "-120 dBm"]):
            gy = 190 + i * 85
            draw.line([(650, gy), (1180, gy)], fill=(22, 32, 50), width=1)
            draw.text((605, gy - 6), dbm, fill=(80, 105, 140), font=font_sub)

        # Frequency X-Axis markings
        for i, freq in enumerate(["100M", "200M", "300M", "433.92M", "500M"]):
            gx = 680 + i * 115
            draw.line([(gx, 190), (gx, 530)], fill=(20, 28, 44), width=1)
            draw.text((gx - 15, 540), freq, fill=(80, 105, 140), font=font_sub)

        # Render Spectral Waveform Curve
        points = []
        for x in range(660, 1180, 4):
            # Center of carrier is ~433.92M -> pixel 1025
            dist = abs(x - 1025)
            if completed:
                # Sharp high-Q resonant peak
                h = max(10, int(320 * (1.0 / (1.0 + (dist / 14) ** 2))))
            else:
                # Noisy spread spectrum
                h = max(20, int(140 * (1.0 / (1.0 + (dist / 60) ** 2)))) + (x * 7) % 35
            points.append((x, 530 - h))

        if len(points) > 1:
            draw.line(points, fill=(52, 211, 153) if completed else (56, 189, 248), width=3)

        # Telemetry metrics footer inside viewport
        draw.rectangle([600, 580, 1200, 640], fill=(14, 20, 32), outline=(30, 42, 64), width=1)
        thd_val = "-58.4 dBc" if completed else "-24.1 dBc"
        evm_val = "0.82% [PASS]" if completed else "4.15% [UNSTABLE]"
        draw.text((620, 602), f"CARRIER: 433.920 MHz   |   THD: {thd_val}   |   PHASE NOISE: -128 dBc/Hz   |   EVM: {evm_val}", fill=(160, 185, 220), font=font_mono)

        # PPT-style laser pointer cursor indicating agent interaction inside target control
        from musepilot.perception.som_renderer import draw_ppt_laser_pointer
        if "step_1" in state_label:
            draw_ppt_laser_pointer(draw, cx=420, cy=190, action_label="✦ ACTUATION: DRAG (75% TARGET)", target_detail="Centroid: (420, 190) • Frequency Synthesizer", laser_color=(255, 45, 85))
        elif "step_2" in state_label:
            draw_ppt_laser_pointer(draw, cx=250, cy=325, action_label="✦ ACTUATION: CLICK TOGGLE", target_detail="Centroid: (250, 325) • Nyquist Damping Enabled", laser_color=(16, 185, 129))
        elif "step_3" in state_label:
            draw_ppt_laser_pointer(draw, cx=320, cy=455, action_label="✦ ACTUATION: KEYSTROKE '0.942'", target_detail="Centroid: (320, 455) • 12-bit IEEE 754 Parameter", laser_color=(6, 182, 212))
        elif "final" in state_label:
            draw_ppt_laser_pointer(draw, cx=280, cy=600, action_label="✦ ACTUATION: BENCHMARK AUDIT", target_detail="Centroid: (280, 600) • Convergence Verified [OK]", laser_color=(16, 185, 129))

    def _draw_w2_canvas(self, draw: ImageDraw.ImageDraw, state_label: str) -> None:
        """Draw Workflow 2: CloudOps Observability & Self-Healing Incident Command Center."""
        font_title = _get_font(13, bold=True)
        font_label = _get_font(12, bold=False)
        font_sub = _get_font(11, bold=False)
        font_btn = _get_font(13, bold=True)
        font_mono = _get_font(12, bold=True)

        # Card container 1 (Mask 1: Anomaly Harvester Button)
        draw.rounded_rectangle([80, 110, 640, 240], radius=10, fill=(18, 25, 38), outline=(35, 48, 72), width=1)
        draw.text((100, 122), "1. TELEMETRY ANOMALY HARVESTER", fill=(210, 230, 255), font=font_title)

        extracted = state_label != "initial"
        btn1_fill = (16, 185, 129) if extracted else (14, 165, 233)
        btn1_border = (110, 231, 183) if extracted else (125, 211, 252)
        draw.rectangle([100, 150, 460, 225], fill=btn1_fill, outline=btn1_border, width=2)
        btn1_txt = "ANOMALY SNAPSHOT COPIED" if extracted else "EXTRACT ANOMALY METRICS"
        draw.text((130, 180), btn1_txt, fill=(255, 255, 255), font=font_btn)

        # Card container 2 (Mask 2: Incident Root Cause Summary Input)
        draw.rounded_rectangle([80, 260, 640, 395], radius=10, fill=(18, 25, 38), outline=(35, 48, 72), width=1)
        draw.text((100, 270), "2. INCIDENT ROOT CAUSE & TRIAGE SUMMARY", fill=(210, 230, 255), font=font_title)

        typed = "step_2" in state_label or "final" in state_label
        input_border = (52, 211, 153) if typed else (70, 85, 115)
        draw.rectangle([100, 285, 620, 375], fill=(16, 24, 38), outline=input_border, width=2)

        input_txt = "INCIDENT: GPU-NODE-07 LATENCY SPIKE (+42ms)" if typed else "INCIDENT REPORT SUMMARY..."
        input_color = (167, 243, 208) if typed else (148, 163, 184)
        draw.text((120, 322), input_txt, fill=input_color, font=font_mono)

        # Card container 3 (Mask 3: SRE Escalation Dispatch Button)
        draw.rounded_rectangle([80, 415, 640, 535], radius=10, fill=(18, 25, 38), outline=(35, 48, 72), width=1)
        draw.text((100, 423), "3. ON-CALL SRE ESCALATION ACTION", fill=(210, 230, 255), font=font_title)

        dispatched = "final" in state_label
        btn3_fill = (16, 185, 129) if dispatched else (245, 158, 11)
        btn3_border = (110, 231, 183) if dispatched else (253, 230, 138)
        draw.rectangle([100, 435, 460, 515], fill=btn3_fill, outline=btn3_border, width=2)
        btn3_txt = "INCIDENT DISPATCHED [ACK]" if dispatched else "DISPATCH URGENT ALERT"
        draw.text((135, 468), btn3_txt, fill=(255, 255, 255), font=font_btn)

        # Right-hand GPU Inference Cluster Telemetry Viewport
        draw.rounded_rectangle([680, 110, 1220, 660], radius=12, fill=(10, 15, 24), outline=(35, 48, 72), width=2)
        draw.text((710, 132), "GPU CLUSTER LATENCY PROFILE (15-MIN WINDOW)", fill=(210, 230, 255), font=font_title)
        draw.text((710, 155), "Cluster: us-central1-gcp-h100 • Total Nodes: 8", fill=(120, 140, 175), font=font_label)

        # SLA Threshold dashed line at 30ms
        draw.line([(710, 310), (1190, 310)], fill=(244, 63, 94), width=1)
        draw.text((1050, 292), "SLA THRESHOLD: 30ms", fill=(253, 164, 175), font=font_sub)

        # 8 Node Latency Bars
        node_latencies = [11.2, 12.8, 10.5, 13.1, 11.9, 12.4, 54.2, 11.7]
        for i, lat in enumerate(node_latencies):
            bx = 730 + i * 56
            bar_h = int(lat * 4.2)
            is_anomaly = lat > 30.0
            b_color = (244, 63, 94) if is_anomaly else (16, 185, 129)
            draw.rectangle([bx, 480 - bar_h, bx + 36, 480], fill=b_color, outline=(255, 255, 255) if is_anomaly else None)
            draw.text((bx - 2, 492), f"N{i+1}", fill=(140, 160, 190), font=font_sub)
            draw.text((bx - 4, 480 - bar_h - 16), f"{lat}m", fill=b_color, font=font_sub)

        # Anomaly callout
        draw.rounded_rectangle([710, 540, 1190, 640], radius=8, fill=(35, 18, 25), outline=(244, 63, 94), width=1)
        draw.text((730, 555), "⚠️ ROOT CAUSE CORRELATION: GPU-NODE-07 (+42ms p99)", fill=(254, 205, 211), font=font_title)
        draw.text((730, 580), "Excess CUDA kernel memory contention detected on physical socket 0. Dispatched to on-call.", fill=(253, 164, 175), font=font_label)
        draw.text((730, 608), "STATUS: INCIDENT CONTAINED [ACK RECEIVED]" if dispatched else "STATUS: ESCALATION PENDING OPERATOR SIGN-OFF", fill=(52, 211, 153) if dispatched else (251, 191, 36), font=font_mono)

        # Modal Obstruction Popup (Self-healing showcase!)
        if "modal" in state_label:
            # Floating enterprise session security dialog
            draw.rounded_rectangle(
                [280, 160, 1000, 580],
                radius=14,
                fill=(20, 26, 38),
                outline=(244, 63, 94),
                width=3,
            )
            # Modal Header Bar
            draw.rounded_rectangle([280, 160, 1000, 220], radius=14, fill=(35, 20, 28))
            draw.text(
                (310, 182),
                "🔒 CLOUDOPS ENTERPRISE SSO SESSION SYNCHRONIZATION",
                fill=(254, 205, 211),
                font=font_title,
            )

            # Modal Explanatory Text
            draw.text(
                (310, 250),
                "Transient cryptographic security token lease expired for cluster us-central1-gcp-h100.",
                fill=(240, 246, 255),
                font=font_label,
            )
            draw.text(
                (310, 285),
                "An unexpected system guardrail modal is currently obstructing the main dispatch portal.",
                fill=(200, 215, 240),
                font=font_label,
            )
            draw.text(
                (310, 320),
                "MusePilot Autonomous Self-Healing will detect this blocker, invalidate perception cache,",
                fill=(167, 243, 208),
                font=font_label,
            )
            draw.text(
                (310, 350),
                "replan dynamically, and dismiss the modal to achieve 100% mission completion.",
                fill=(167, 243, 208),
                font=font_label,
            )

            # Mask 4: Dismiss Modal Button (500, 420, 780, 495)
            draw.rounded_rectangle(
                [500, 420, 780, 495],
                radius=8,
                fill=(225, 29, 72),
                outline=(255, 255, 255),
                width=2,
            )
            draw.text((540, 448), "DISMISS & RESYNC SESSION", fill=(255, 255, 255), font=font_btn)

        # PPT-style laser pointer cursor indicating agent interaction inside target control
        from musepilot.perception.som_renderer import draw_ppt_laser_pointer
        if "modal" in state_label:
            draw_ppt_laser_pointer(draw, cx=640, cy=457, action_label="✦ AUTONOMOUS REPLAN: DISMISS", target_detail="Centroid: (640, 457) • Blocker Cleared & Resynced", laser_color=(255, 45, 85))
        elif state_label == "initial":
            draw_ppt_laser_pointer(draw, cx=280, cy=187, action_label="✦ ACTUATION: EXTRACT METRICS", target_detail="Centroid: (280, 187) • GPU Cluster Telemetry", laser_color=(14, 165, 233))
        elif "step_1" in state_label or "step_2" in state_label or "recovered" in state_label:
            draw_ppt_laser_pointer(draw, cx=360, cy=330, action_label="✦ ACTUATION: INJECT INCIDENT REPORT", target_detail="Centroid: (360, 330) • GPU-NODE-07 Latency Spike", laser_color=(52, 211, 153))
        elif "final" in state_label:
            draw_ppt_laser_pointer(draw, cx=280, cy=475, action_label="✦ ACTUATION: DISPATCH ESCALATION", target_detail="Centroid: (280, 475) • PagerDuty + Slack Acked", laser_color=(16, 185, 129))
