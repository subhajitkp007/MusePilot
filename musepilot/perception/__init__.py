# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Perception module: screen capture, SAM 3.1 segmentation, and Set-of-Mark rendering."""

from __future__ import annotations

from musepilot.perception.capture import CapturedFrame, ScreenCaptureEngine, compute_image_hash
from musepilot.perception.sam_client import SAM31PerceptionClient, compute_bbox_centroid
from musepilot.perception.som_renderer import SetOfMarkRenderer

__all__ = [
    "CapturedFrame",
    "SAM31PerceptionClient",
    "ScreenCaptureEngine",
    "SetOfMarkRenderer",
    "compute_bbox_centroid",
    "compute_image_hash",
]
