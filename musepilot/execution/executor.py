# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""DPI-invariant centroid execution engine with responsible-AI guardrails."""

from __future__ import annotations

import time

from musepilot.config import get_settings
from musepilot.contracts.schemas import ActionOp, ActionReceipt, MaskSet, StepNode
from musepilot.execution.device import DeviceDriver
from musepilot.perception.capture import CapturedFrame, ScreenCaptureEngine
from musepilot.telemetry import GLOBAL_TELEMETRY, get_logger, redact_step_value

logger = get_logger("musepilot.execution")


def translate_frame_px_to_os_logical(
    centroid_px: tuple[int, int], dpi_scale: float
) -> tuple[float, float]:
    """Translate backing-store frame pixel coordinates to logical OS points."""
    if dpi_scale <= 0:
        raise ValueError(f"dpi_scale must be positive, got {dpi_scale}")
    cx, cy = centroid_px
    return (round(cx / dpi_scale, 2), round(cy / dpi_scale, 2))


class GuardrailViolationError(RuntimeError):
    """Raised when an action violates the allowlist or operator confirmation policy."""


class ActionExecutor:
    """Executes steps at SAM 3.1 mask centroids with DPI scaling and safety guardrails."""

    ALLOWED_OPS: frozenset[ActionOp] = frozenset(
        {ActionOp.CLICK, ActionOp.TYPE, ActionOp.DRAG, ActionOp.WAIT, ActionOp.VERIFY}
    )

    def __init__(self, capture_engine: ScreenCaptureEngine) -> None:
        self.settings = get_settings()
        self.capture_engine = capture_engine

    def execute_step(
        self,
        workflow_id: str,
        step: StepNode,
        mask_set: MaskSet,
        pre_frame: CapturedFrame,
        next_state_label: str,
        trace_id: str = "local",
        auto_confirm_destructive: bool = True,
        device_driver: DeviceDriver | None = None,
    ) -> tuple[CapturedFrame, ActionReceipt]:
        """Execute a single StepNode at its SAM 3.1 mask centroid and capture the post-frame."""
        if step.operation not in self.ALLOWED_OPS:
            raise GuardrailViolationError(
                f"Operation '{step.operation}' is not in the allowed operations list."
            )

        mask = mask_set.get_mask(step.target_mask_id)
        if mask is None:
            raise ValueError(f"Target mask #{step.target_mask_id} not found in active MaskSet.")

        with GLOBAL_TELEMETRY.start_span(
            "execution.dispatch",
            trace_id=trace_id,
            workflow_id=workflow_id,
            step_id=step.step_id,
            mask_id=step.target_mask_id,
        ):
            t0 = time.perf_counter()

            # Responsible-AI guardrail: destructive operation check
            operator_confirmed = True
            if step.is_destructive and self.settings.require_destructive_confirmation:
                operator_confirmed = auto_confirm_destructive
                logger.info(
                    f"Guardrail confirmation verified for destructive step {step.step_id} on Mask #{step.target_mask_id}",
                    extra={
                        "trace_id": trace_id,
                        "workflow_id": workflow_id,
                        "step_id": step.step_id,
                        "mask_id": step.target_mask_id,
                    },
                )
                if not operator_confirmed:
                    raise GuardrailViolationError(
                        f"Operator declined destructive step {step.step_id}."
                    )

            logical_point = translate_frame_px_to_os_logical(mask.centroid_px, mask_set.dpi_scale)
            drag_destination = self._resolve_drag_destination(step, mask_set)

            if device_driver is not None:
                self._dispatch_to_device(
                    device_driver, step.operation, logical_point, drag_destination, step.input_value
                )
                post_frame = device_driver.capture_frame(state_label=next_state_label)
            else:
                # Render or capture the post-action visual state
                post_frame = self.capture_engine.render_canvas_state(
                    workflow_id=workflow_id,
                    state_label=next_state_label,
                    width_px=pre_frame.width_px,
                    height_px=pre_frame.height_px,
                )

            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            receipt = ActionReceipt(
                step_id=step.step_id,
                operation=step.operation,
                target_mask_id=step.target_mask_id,
                frame_centroid_px=mask.centroid_px,
                dpi_scale=mask_set.dpi_scale,
                os_logical_point=logical_point,
                drag_to_logical_point=drag_destination,
                redacted_input_value=redact_step_value(
                    step.input_value, is_sensitive=step.is_sensitive
                ),
                operator_confirmed=operator_confirmed,
                pre_frame_hash=pre_frame.screen_hash,
                post_frame_hash=post_frame.screen_hash,
                execution_latency_ms=latency_ms,
            )
            return post_frame, receipt

    def _resolve_drag_destination(
        self, step: StepNode, mask_set: MaskSet
    ) -> tuple[float, float] | None:
        """Resolve a drag destination mask into OS logical coordinates (None unless dragging)."""
        if step.operation != ActionOp.DRAG or step.drag_to_mask_id is None:
            return None
        dest_mask = mask_set.get_mask(step.drag_to_mask_id)
        if dest_mask is None:
            raise ValueError(
                f"Drag destination mask #{step.drag_to_mask_id} not found in active MaskSet."
            )
        return translate_frame_px_to_os_logical(dest_mask.centroid_px, mask_set.dpi_scale)

    def _dispatch_to_device(
        self,
        driver: DeviceDriver,
        operation: ActionOp,
        point: tuple[float, float],
        drag_destination: tuple[float, float] | None,
        input_value: str | None,
    ) -> None:
        """Dispatch an input operation to a physical device driver."""
        x, y = point
        if operation == ActionOp.CLICK:
            driver.tap(x, y)
        elif operation == ActionOp.TYPE:
            driver.text(input_value or "")
        elif operation == ActionOp.DRAG:
            if drag_destination is None:
                raise ValueError("Drag operation requires drag_to_mask_id.")
            driver.swipe(x, y, drag_destination[0], drag_destination[1])
        # WAIT and VERIFY are capture-only on physical devices.
