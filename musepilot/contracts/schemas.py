# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Strict Pydantic schemas enforcing the Zero-Coordinate Invariant across MusePilot."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ZeroCoordinateViolationError(ValueError):
    """Raised when a planner payload attempts to emit raw [x, y] coordinates."""


class ActionOp(str, Enum):
    """Supported GUI operations in the MusePilot execution engine."""

    CLICK = "click"
    TYPE = "type"
    DRAG = "drag"
    WAIT = "wait"
    VERIFY = "verify"


class MaskMetadata(BaseModel):
    """Pixel-exact UI segment metadata produced by Meta SAM 3.1."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    mask_id: int = Field(..., ge=1, description="1-indexed Set-of-Mark badge ID")
    bbox: tuple[int, int, int, int] = Field(
        ..., description="Bounding box (x1, y1, x2, y2) in backing-store frame pixels"
    )
    centroid_px: tuple[int, int] = Field(
        ..., description="Geometric centroid (cx, cy) in backing-store frame pixels"
    )
    area_px: int = Field(..., ge=1, description="Segmented mask pixel area")
    confidence: float = Field(..., ge=0.0, le=1.0, description="SAM 3.1 predicted IoU score")
    semantic_tag: str = Field(
        default="ui_element",
        description="Visual region hint for debugging and telemetry",
    )
    polygon: list[tuple[int, int]] = Field(
        default_factory=list,
        description="Boundary polygon vertices in frame pixel coordinates",
    )


class MaskSet(BaseModel):
    """Collection of SAM 3.1 masks for a single captured screen frame."""

    model_config = ConfigDict(extra="forbid")

    screen_hash: str = Field(..., description="SHA-256 hash of raw screen frame")
    width_px: int = Field(..., gt=0)
    height_px: int = Field(..., gt=0)
    dpi_scale: float = Field(default=2.0, gt=0.0)
    model_id: str = Field(default="meta-models/sam-3.1")
    cached: bool = Field(default=False)
    latency_ms: float = Field(default=0.0, ge=0.0)
    masks: list[MaskMetadata] = Field(default_factory=list)

    def get_mask(self, mask_id: int) -> MaskMetadata | None:
        """Look up a mask by its 1-indexed Set-of-Mark ID."""
        for mask in self.masks:
            if mask.mask_id == mask_id:
                return mask
        return None

    @property
    def valid_mask_ids(self) -> set[int]:
        """Return the set of all live mask IDs on the current screen."""
        return {m.mask_id for m in self.masks}


FORBIDDEN_COORDINATE_KEYS = frozenset(
    {"x", "y", "coords", "coordinates", "point", "click_x", "click_y", "bbox", "raw_xy"}
)


class StepNode(BaseModel):
    """A single planned action referencing a SAM 3.1 mask ID (never raw coordinates)."""

    model_config = ConfigDict(extra="forbid")

    step_id: int = Field(..., ge=1)
    operation: ActionOp
    target_mask_id: int = Field(..., ge=1, description="SAM 3.1 Set-of-Mark badge ID to act upon")
    drag_to_mask_id: int | None = Field(
        default=None, ge=1, description="Destination mask ID when operation is 'drag'"
    )
    input_value: str | None = Field(
        default=None, description="Text payload when operation is 'type'"
    )
    is_sensitive: bool = Field(
        default=False, description="If True, value is redacted in logs and traces"
    )
    is_destructive: bool = Field(
        default=False, description="If True, requires human operator confirmation"
    )
    expected_outcome: str = Field(
        ..., min_length=5, description="Natural-language post-condition for visual verification"
    )
    reasoning: str = Field(default="", description="Planner rationale for selecting target_mask_id")

    @model_validator(mode="before")
    @classmethod
    def reject_raw_coordinates(cls, data: Any) -> Any:
        """Enforce the Zero-Coordinate Invariant at the schema boundary."""
        if isinstance(data, dict):
            violating_keys = FORBIDDEN_COORDINATE_KEYS.intersection(data.keys())
            if violating_keys:
                raise ZeroCoordinateViolationError(
                    f"Zero-Coordinate Invariant violated: Planner emitted forbidden coordinate "
                    f"fields {sorted(violating_keys)}. Only 'target_mask_id' is permitted."
                )
        return data


class StepDAG(BaseModel):
    """Structured multi-step execution plan emitted by Meta Muse Spark."""

    model_config = ConfigDict(extra="forbid")

    plan_version: str = Field(default="planner_som_v1")
    model_id: str = Field(default="meta-models/muse-spark")
    workflow_id: str
    intent: str
    plan_summary: str
    latency_ms: float = Field(default=0.0, ge=0.0)
    steps: list[StepNode] = Field(..., min_length=1)

    def validate_against_mask_set(self, mask_set: MaskSet) -> None:
        """Verify that every planned step references a live SAM 3.1 mask ID."""
        live_ids = mask_set.valid_mask_ids
        for step in self.steps:
            if step.target_mask_id not in live_ids:
                raise ValueError(
                    f"Step {step.step_id} references unknown target_mask_id={step.target_mask_id}. "
                    f"Live mask IDs: {sorted(live_ids)}"
                )
            if step.drag_to_mask_id is not None and step.drag_to_mask_id not in live_ids:
                raise ValueError(
                    f"Step {step.step_id} references unknown drag_to_mask_id={step.drag_to_mask_id}."
                )


class ActionReceipt(BaseModel):
    """Execution receipt proving DPI-normalized centroid translation and input dispatch."""

    model_config = ConfigDict(extra="forbid")

    step_id: int
    operation: ActionOp
    target_mask_id: int
    frame_centroid_px: tuple[int, int]
    dpi_scale: float
    os_logical_point: tuple[float, float]
    redacted_input_value: str | None = None
    operator_confirmed: bool = True
    pre_frame_hash: str
    post_frame_hash: str
    execution_latency_ms: float


class VerificationVerdict(BaseModel):
    """Closed-loop visual state verification verdict from Muse Spark Open."""

    model_config = ConfigDict(extra="forbid")

    verifier_version: str = Field(default="verifier_eval_v1")
    model_id: str = Field(default="meta-models/muse-spark-open-1026")
    partner_provider: str = Field(default="baseten")
    passed: bool
    confidence: float = Field(..., ge=0.0, le=1.0)
    roi_pixel_delta: float = Field(
        ..., ge=0.0, le=1.0, description="Measured structural pixel change ratio in ROI"
    )
    observed_change: str
    obstruction_detected: bool = False
    retry_hint: str | None = None
    latency_ms: float = Field(default=0.0, ge=0.0)


class VoiceTranscript(BaseModel):
    """Spoken intent transcribed via Meta Muse Voice Transcribe."""

    model_config = ConfigDict(extra="forbid")

    model_id: str = Field(default="meta-models/muse-voice-transcribe")
    transcript: str
    confidence: float = Field(default=0.99, ge=0.0, le=1.0)
    audio_duration_sec: float = Field(default=2.8, ge=0.0)
    latency_ms: float = Field(default=0.0, ge=0.0)


class StepExecutionRecord(BaseModel):
    """Complete audit record for a single step attempt (including retries/self-healing)."""

    model_config = ConfigDict(extra="forbid")

    attempt_number: int = Field(..., ge=1)
    step: StepNode
    receipt: ActionReceipt
    verdict: VerificationVerdict
    self_healed: bool = False
    healing_action: str | None = None


class MetricsSummary(BaseModel):
    """Quantitative benchmark metrics computed over a run trace."""

    model_config = ConfigDict(extra="forbid")

    total_steps_planned: int
    total_steps_completed: int
    mask_centroid_hit_rate: float = Field(..., ge=0.0, le=1.0)
    verification_pass_rate: float = Field(..., ge=0.0, le=1.0)
    self_healing_recoveries: int = 0
    median_sam_latency_ms: float = 0.0
    median_planner_latency_ms: float = 0.0
    median_verifier_latency_ms: float = 0.0


class RunTrace(BaseModel):
    """Replayable, deterministic full-run trace persisted to JSON."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str
    workflow_id: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    execution_mode: str
    voice_intake: VoiceTranscript | None = None
    initial_mask_set: MaskSet
    plan: StepDAG
    records: list[StepExecutionRecord] = Field(default_factory=list)
    status: str = Field(default="COMPLETED")
    metrics: MetricsSummary
