# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Execution module: DPI-normalized centroid math and guarded input dispatch."""

from musepilot.execution.executor import (
    ActionExecutor,
    GuardrailViolationError,
    translate_frame_px_to_os_logical,
)

__all__ = [
    "ActionExecutor",
    "GuardrailViolationError",
    "translate_frame_px_to_os_logical",
]

