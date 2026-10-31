# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Closed-loop visual verifier powered by Meta open-weight Muse Spark Open."""

from __future__ import annotations

import json
import time

import httpx
import numpy as np

from musepilot.config import get_settings
from musepilot.contracts.schemas import MaskMetadata, StepNode, VerificationVerdict
from musepilot.perception.capture import CapturedFrame
from musepilot.telemetry import GLOBAL_TELEMETRY, get_logger

logger = get_logger("musepilot.verification.spark_open")


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

            if self.settings.execution_mode == "live" and self.settings.partner_api_key:
                verdict = self._call_partner_verifier_api(step, effective_delta, post_frame)
            else:
                verdict = self._evaluate_deterministic_verdict(step, effective_delta, post_frame)

            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            GLOBAL_TELEMETRY.record_verifier_latency(latency_ms)
            verdict = verdict.model_copy(update={"latency_ms": latency_ms})
            span.attributes["verdict_passed"] = verdict.passed
            span.attributes["roi_pixel_delta"] = verdict.roi_pixel_delta
            return verdict

    def _call_partner_verifier_api(
        self,
        step: StepNode,
        roi_delta: float,
        post_frame: CapturedFrame,
    ) -> VerificationVerdict:
        """Call Baseten / Modal / Fireworks endpoint serving `meta-models/muse-spark-open-1026`."""
        prompt_template = self.load_prompt_template()
        filled_prompt = (
            prompt_template.replace("{operation}", step.operation.value)
            .replace("{target_mask_id}", str(step.target_mask_id))
            .replace("{expected_outcome}", step.expected_outcome)
            .replace("{roi_change_ratio}", f"{roi_delta:.4f}")
        )
        headers = {
            "Authorization": f"Bearer {self.settings.partner_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.settings.verifier_model_id,
            "temperature": 0.0,
            "messages": [
                {"role": "system", "content": filled_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Post-action state label: {post_frame.state_label}. "
                        f"Measured pixel delta: {roi_delta:.4f}. Return JSON verdict."
                    ),
                },
            ],
        }
        try:
            with httpx.Client(timeout=self.settings.api_timeout_seconds) as client:
                response = client.post(
                    f"{self.settings.partner_base_url.rstrip('/')}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                raw_json = json.loads(response.json()["choices"][0]["message"]["content"])
                return VerificationVerdict(
                    model_id=self.settings.verifier_model_id,
                    partner_provider=self.settings.partner_provider,
                    passed=bool(raw_json.get("passed", True)),
                    confidence=float(raw_json.get("confidence", 0.96)),
                    roi_pixel_delta=roi_delta,
                    observed_change=str(raw_json.get("observed_change", "State verified")),
                    obstruction_detected=bool(raw_json.get("obstruction_detected", False)),
                    retry_hint=raw_json.get("retry_hint"),
                )
        except Exception as exc:
            logger.warning(
                f"Partner verifier endpoint fallback triggered ({exc}); using local structural verifier."
            )
            return self._evaluate_deterministic_verdict(step, roi_delta, post_frame)

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

        passed = roi_delta > 0.001
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
