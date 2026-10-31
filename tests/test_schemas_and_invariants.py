# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Unit tests for Zero-Coordinate Invariant and Pydantic data contracts."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from musepilot.config import MusePilotSettings
from musepilot.contracts.schemas import (
    ActionOp,
    MaskMetadata,
    MaskSet,
    StepDAG,
    StepNode,
    ZeroCoordinateViolationError,
)


def test_step_node_accepts_valid_mask_id() -> None:
    step = StepNode(
        step_id=1,
        operation=ActionOp.CLICK,
        target_mask_id=4,
        expected_outcome="Simulation benchmark button turns emerald green",
        reasoning="Mask #4 corresponds to the Run Benchmark button",
    )
    assert step.target_mask_id == 4
    assert step.operation == ActionOp.CLICK


@pytest.mark.parametrize(
    "forbidden_field",
    ["x", "y", "coords", "coordinates", "point", "click_x", "click_y", "bbox", "raw_xy"],
)
def test_zero_coordinate_invariant_rejects_raw_coordinates(forbidden_field: str) -> None:
    payload = {
        "step_id": 1,
        "operation": "click",
        "target_mask_id": 2,
        "expected_outcome": "Button shows active state",
        forbidden_field: [250, 410],
    }
    with pytest.raises((ZeroCoordinateViolationError, ValidationError)):
        StepNode.model_validate(payload)


def test_step_dag_validates_live_mask_ids() -> None:
    mask_set = MaskSet(
        screen_hash="abc12345",
        width_px=1280,
        height_px=800,
        masks=[
            MaskMetadata(
                mask_id=1,
                bbox=(10, 10, 100, 50),
                centroid_px=(55, 30),
                area_px=3600,
                confidence=0.99,
            )
        ],
    )
    valid_dag = StepDAG(
        workflow_id="w1",
        intent="Click button 1",
        plan_summary="Click mask 1",
        steps=[
            StepNode(
                step_id=1,
                operation=ActionOp.CLICK,
                target_mask_id=1,
                expected_outcome="Button 1 activated",
            )
        ],
    )
    valid_dag.validate_against_mask_set(mask_set)

    invalid_dag = StepDAG(
        workflow_id="w1",
        intent="Click missing mask 99",
        plan_summary="Invalid mask reference",
        steps=[
            StepNode(
                step_id=1,
                operation=ActionOp.CLICK,
                target_mask_id=99,
                expected_outcome="Should fail validation",
            )
        ],
    )
    with pytest.raises(ValueError, match="unknown target_mask_id=99"):
        invalid_dag.validate_against_mask_set(mask_set)


def test_open_weight_verifier_model_validation() -> None:
    valid = MusePilotSettings(verifier_model_id="meta-models/muse-spark-open-1026")
    assert valid.verifier_model_id == "meta-models/muse-spark-open-1026"

    with pytest.raises(ValidationError, match="Meta open-weight model"):
        MusePilotSettings(verifier_model_id="proprietary/closed-verifier-v1")
