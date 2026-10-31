# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Unit tests for DPI scaling math, SAM 3.1 caching, and Set-of-Mark rendering."""

from __future__ import annotations

import pytest

from musepilot.execution import translate_frame_px_to_os_logical
from musepilot.perception import (
    SAM31PerceptionClient,
    ScreenCaptureEngine,
    SetOfMarkRenderer,
    compute_image_hash,
)


def test_retina_dpi_coordinate_translation() -> None:
    # Backing store pixel (640, 400) on 2.0x macOS Retina -> (320.0, 200.0) OS logical point
    assert translate_frame_px_to_os_logical((640, 400), dpi_scale=2.0) == (320.0, 200.0)
    # Standard 1.0x display -> (640.0, 400.0)
    assert translate_frame_px_to_os_logical((640, 400), dpi_scale=1.0) == (640.0, 400.0)

    with pytest.raises(ValueError, match="dpi_scale must be positive"):
        translate_frame_px_to_os_logical((100, 100), dpi_scale=0.0)


def test_sam31_perception_caching_and_invalidation() -> None:
    capture = ScreenCaptureEngine(dpi_scale=2.0)
    sam = SAM31PerceptionClient()

    frame = capture.render_canvas_state(workflow_id="w1", state_label="initial")
    first_masks = sam.segment_frame(frame, workflow_id="w1")
    assert first_masks.cached is False
    assert len(first_masks.masks) == 4

    second_masks = sam.segment_frame(frame, workflow_id="w1")
    assert second_masks.cached is True
    assert second_masks.screen_hash == first_masks.screen_hash

    sam.invalidate_cache()
    third_masks = sam.segment_frame(frame, workflow_id="w1")
    assert third_masks.cached is False


def test_set_of_mark_renderer_draws_badges() -> None:
    capture = ScreenCaptureEngine(dpi_scale=2.0)
    sam = SAM31PerceptionClient()
    renderer = SetOfMarkRenderer()

    frame = capture.render_canvas_state(workflow_id="w1", state_label="initial")
    mask_set = sam.segment_frame(frame, workflow_id="w1")
    som_img = renderer.render_som_overlay(
        base_image=frame.image,
        mask_set=mask_set,
        active_target_mask_id=1,
        verified_mask_ids={2},
    )
    assert som_img.size == frame.image.size
    assert compute_image_hash(som_img) != frame.screen_hash

