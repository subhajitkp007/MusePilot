# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Verification module powered by Meta Muse Spark Open."""

from __future__ import annotations

from musepilot.verification.spark_open_verifier import (
    SparkOpenVerifier,
    compute_roi_pixel_delta,
)

__all__ = ["SparkOpenVerifier", "compute_roi_pixel_delta"]
