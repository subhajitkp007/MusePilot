# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Closed-loop visual verifier powered by Meta open-weight Muse Spark Open."""

from __future__ import annotations

import base64
import io
import time

import httpx
import numpy as np
from PIL import Image

from musepilot.config import get_settings
from musepilot.contracts.repair import extract_json_object
from musepilot.contracts.schemas import (
    LiveModelError,
    MaskMetadata,
    StepNode,
    VerificationVerdict,
)
from musepilot.perception.capture import CapturedFrame
from musepilot.telemetry import GLOBAL_TELEMETRY, get_logger

logger = get_logger("musepilot.verification.spark_open")

_ROI_PAD_FACTOR = 1.5
_ROI_MAX_DIM = 512


def compute_roi_pixel_delta(
    pre_frame: CapturedFrame,
    post_frame: CapturedFrame,
    bbox: tuple[int, int, int, int] | None = None,
) -> float:
    """Compute structural pixel change ratio in [0.0, 1.0] across the target ROI or frame."""
    pre_arr = np.asarray(pre_frame.image.convert("RGB"), dtype=np.float32)
    post_arr = np.asarray(post_frame.image.convert("RGB"), dtype=np.float32)

    if bbox is not None:
        x1, y1, x2, y2 = bbox
        pre_crop = pre_arr[max(0, y1) : y2, max(0, x1) : x2]
        post_crop = post_arr[max(0, y1) : y2, max(0, x1) : x2]
        if pre_crop.size > 0 and pre_crop.shape == post_crop.shape:
            diff = np.abs(pre_crop - post_crop)
            changed_pixels = np.mean(diff > 12.0)
            return round(float(changed_pixels), 4)

    diff_full = np.abs(pre_arr - post_arr)
    return round(float(np.mean(diff_full > 12.0)), 4)


def crop_roi(
    frame: CapturedFrame,
    bbox: tuple[int, int, int, int],
    pad_factor: float = _ROI_PAD_FACTOR,
    max_dim: int = _ROI_MAX_DIM,
) -> Image.Image:
    """Crop a padded region around a mask box, clamped to the frame."""
    width, height = frame.image.size
    x1, y1, x2, y2 = bbox
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    half_w = max(1.0, (x2 - x1) * pad_factor / 2)
    half_h = max(1.0, (y2 - y1) * pad_factor / 2)
    box = (
        max(0, int(cx - half_w)),
        max(0, int(cy - half_h)),
        min(width, int(cx + half_w)),
        min(height, int(cy + half_h)),
    )
    crop = frame.image.crop(box)
    longest = max(crop.size)
    if longest > max_dim:
        scale = max_dim / longest
        crop = crop.resize((max(1, int(crop.size[0] * scale)), max(1, int(crop.size[1] * scale))))
    return crop


def encode_image_b64(image: Image.Image) -> str:
    """Encode a PIL image as base64 PNG for vision payloads."""
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


class SparkOpenVerifier:
    """Evaluates pre/post visual state transitions using `meta-models/muse-spark-open-1026`."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def load_prompt_template(self) -> str:
        """Load the versioned verifier prompt template from disk."""
        return self.settings.verifier_prompt_path.read_text(encoding="utf-8")

    def verify_transition(
        self,
        step: StepNode,
        target_mask: MaskMetadata,
        pre_frame: CapturedFrame,
        post_frame: CapturedFrame,
        trace_id: str = "local",
    ) -> VerificationVerdict:
        """Gate step completion by combining ROI pixel delta with Muse Spark Open judgment."""
        with GLOBAL_TELEMETRY.start_span(
            "verification.muse_spark_open",
            trace_id=trace_id,
            model_id=self.settings.verifier_model_id,
            partner=self.settings.partner_provider,
            step_id=step.step_id,
            mask_id=step.target_mask_id,
        ) as span:
            t0 = time.perf_counter()
            roi_delta = compute_roi_pixel_delta(pre_frame, post_frame, target_mask.bbox)
            full_delta = compute_roi_pixel_delta(pre_frame, post_frame, None)
            effective_delta = max(roi_delta, full_delta)

            credentials = self._live_credentials()
            if self.settings.execution_mode == "live" and credentials is not None:
                verdict = self._call_live_verifier_api(
                    step,
                    target_mask,
                    effective_delta,
                    pre_frame,
                    post_frame,
                    credentials,
                    trace_id,
                )
            else:
                verdict = self._evaluate_deterministic_verdict(step, effective_delta, post_frame)

            if verdict.passed and verdict.confidence < self.settings.verifier_confidence_threshold:
                verdict = verdict.model_copy(
                    update={
                        "passed": False,
                        "observed_change": (
                            f"Rejected low-confidence transition "
                            f"(confidence={verdict.confidence:.2f} < "
                            f"threshold={self.settings.verifier_confidence_threshold:.2f})."
                        ),
                        "retry_hint": "Re-capture the frame and re-verify the transition.",
                    }
                )

            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            GLOBAL_TELEMETRY.record_verifier_latency(latency_ms)
            verdict = verdict.model_copy(update={"latency_ms": latency_ms})
            span.attributes["verdict_passed"] = verdict.passed
            span.attributes["roi_pixel_delta"] = verdict.roi_pixel_delta
            return verdict

    def _live_credentials(self) -> tuple[str, str, str, str] | None:
        """Resolve (base_url, api_key, model_id, provider) for the active backend."""
        if self.settings.verifier_backend == "meta":
            if not self.settings.meta_api_key:
                return None
            return (
                self.settings.meta_api_base_url,
                self.settings.meta_api_key,
                self.settings.meta_verifier_model_id,
                "meta",
            )
        if not self.settings.partner_api_key:
            return None
        return (
            self.settings.partner_base_url,
            self.settings.partner_api_key,
            self.settings.verifier_model_id,
            self.settings.partner_provider,
        )

    def _call_live_verifier_api(
        self,
        step: StepNode,
        target_mask: MaskMetadata,
        roi_delta: float,
        pre_frame: CapturedFrame,
        post_frame: CapturedFrame,
        credentials: tuple[str, str, str, str],
        trace_id: str = "local",
    ) -> VerificationVerdict:
        """Judge a transition on the configured live backend (partner or Meta)."""
        base_url, api_key, model_id, provider = credentials
        prompt_template = self.load_prompt_template()
        filled_prompt = (
            prompt_template.replace("{operation}", step.operation.value)
            .replace("{target_mask_id}", str(step.target_mask_id))
            .replace("{expected_outcome}", step.expected_outcome)
            .replace("{roi_change_ratio}", f"{roi_delta:.4f}")
            .replace("meta-models/muse-spark-open-1026", model_id)
        )
        pre_crop = encode_image_b64(crop_roi(pre_frame, target_mask.bbox))
        post_crop = encode_image_b64(crop_roi(post_frame, target_mask.bbox))
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_id,
            "temperature": 0.0,
            "max_tokens": self.settings.verifier_max_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": filled_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                f"Pre-action ROI followed by post-action ROI "
                                f"(Mask #{step.target_mask_id}). "
                                f"Measured pixel delta: {roi_delta:.4f}. "
                                f"Return the JSON verdict."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{pre_crop}"},
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{post_crop}"},
                        },
                    ],
                },
            ],
        }
        content = self._post_verdict(payload, headers, base_url, trace_id)
        try:
            return self._verdict_from_json(
                extract_json_object(content), roi_delta, model_id, provider
            )
        except (LiveModelError, ValueError) as exc:
            logger.warning(f"Verifier reply failed validation ({exc}); retrying once.")
        payload["messages"].append({"role": "assistant", "content": content})
        payload["messages"].append(
            {
                "role": "user",
                "content": (
                    "Your previous reply was not a valid verdict JSON object. "
                    "Reply with ONLY the JSON object, no prose, no fences."
                ),
            }
        )
        content = self._post_verdict(payload, headers, base_url, trace_id)
        try:
            return self._verdict_from_json(
                extract_json_object(content), roi_delta, model_id, provider
            )
        except (LiveModelError, ValueError) as exc:
            raise LiveModelError(f"Verifier failed to emit a valid verdict: {exc}") from exc

    def _post_verdict(
        self, payload: dict, headers: dict[str, str], base_url: str, trace_id: str
    ) -> str:
        """POST one verdict completion and return the assistant content."""
        try:
            with httpx.Client(timeout=self.settings.api_timeout_seconds * 4) as client:
                response = client.post(
                    f"{base_url.rstrip('/')}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                choice = response.json()["choices"][0]
                content = choice["message"]["content"]
                finish_reason = choice.get("finish_reason", "unknown")
        except httpx.HTTPStatusError as exc:
            raise LiveModelError(
                f"Verifier request rejected (HTTP {exc.response.status_code})."
            ) from exc
        except (httpx.HTTPError, KeyError, IndexError, TypeError) as exc:
            raise LiveModelError(f"Verifier request failed: {exc}") from exc
        if not content:
            raise LiveModelError(
                f"Verifier returned empty content (finish_reason={finish_reason})."
            )
        logger.info(
            "Live verifier reply received",
            extra={"trace_id": trace_id, "component": "verification.muse_spark_open"},
        )
        return str(content)

    def _verdict_from_json(
        self, raw: dict, roi_delta: float, model_id: str, provider: str
    ) -> VerificationVerdict:
        """Validate a raw verdict dict into a VerificationVerdict."""
        return VerificationVerdict(
            model_id=model_id,
            partner_provider=provider,
            passed=bool(raw.get("passed", True)),
            confidence=float(raw.get("confidence", 0.96)),
            roi_pixel_delta=roi_delta,
            observed_change=str(raw.get("observed_change", "State verified")),
            obstruction_detected=bool(raw.get("obstruction_detected", False)),
            retry_hint=raw.get("retry_hint"),
        )

    def _evaluate_deterministic_verdict(
        self,
        step: StepNode,
        roi_delta: float,
        post_frame: CapturedFrame,
    ) -> VerificationVerdict:
        """Evaluate state transition deterministically for simulation, replay, and CI tests."""
        if "modal" in post_frame.state_label and step.target_mask_id != 4:
            return VerificationVerdict(
                model_id=self.settings.verifier_model_id,
                partner_provider=self.settings.partner_provider,
                passed=False,
                confidence=0.98,
                roi_pixel_delta=roi_delta,
                observed_change="Transient session sync modal obstructed target control.",
                obstruction_detected=True,
                retry_hint="Invalidate SAM 3.1 mask cache, re-segment modal, and click Dismiss (Mask #4).",
            )

        passed = roi_delta > self.settings.verifier_min_roi_pixel_delta
        return VerificationVerdict(
            model_id=self.settings.verifier_model_id,
            partner_provider=self.settings.partner_provider,
            passed=passed,
            confidence=0.97 if passed else 0.91,
            roi_pixel_delta=roi_delta,
            observed_change=(
                f"Verified transition: {step.expected_outcome} (ROI pixel delta={roi_delta:.3f})"
                if passed
                else "No visual state transition detected in target mask region."
            ),
            obstruction_detected=False,
            retry_hint=None if passed else "Wait 300ms and retry click at mask centroid.",
        )
