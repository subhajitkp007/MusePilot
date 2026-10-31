# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Deterministic trace persistence and golden-trace replay engine."""

from __future__ import annotations

import json
from pathlib import Path

from musepilot.config import get_settings
from musepilot.contracts.schemas import RunTrace
from musepilot.telemetry import get_logger, redact_dict

logger = get_logger("musepilot.trace")


class TraceStore:
    """Persists and replays deterministic JSON execution traces."""

    def __init__(self, trace_dir: Path | None = None) -> None:
        settings = get_settings()
        self.trace_dir = trace_dir or settings.trace_dir
        self.golden_dir = settings.golden_trace_dir
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.golden_dir.mkdir(parents=True, exist_ok=True)

    def save_trace(self, run_trace: RunTrace, *, save_as_golden: bool = False) -> Path:
        """Serialize a RunTrace to disk with automatic sensitive-field redaction."""
        raw_dict = run_trace.model_dump(mode="json")
        sanitized = redact_dict(raw_dict)

        filename = f"trace_{run_trace.workflow_id.lower()}_{run_trace.trace_id}.json"
        out_path = self.trace_dir / filename
        out_path.write_text(json.dumps(sanitized, indent=2), encoding="utf-8")

        # Also update latest symlink/copy for quick dashboard discovery
        latest_path = self.trace_dir / f"latest_{run_trace.workflow_id.lower()}.json"
        latest_path.write_text(json.dumps(sanitized, indent=2), encoding="utf-8")

        if save_as_golden:
            golden_path = self.golden_dir / f"golden_{run_trace.workflow_id.lower()}.json"
            golden_path.write_text(json.dumps(sanitized, indent=2), encoding="utf-8")

        logger.info(
            f"Saved deterministic run trace to {out_path}",
            extra={
                "trace_id": run_trace.trace_id,
                "workflow_id": run_trace.workflow_id,
                "component": "trace.store",
            },
        )
        return out_path

    def load_trace(self, trace_path: Path) -> RunTrace:
        """Load and schema-validate a persisted RunTrace from JSON."""
        raw = json.loads(trace_path.read_text(encoding="utf-8"))
        return RunTrace.model_validate(raw)

    def load_golden_or_latest(self, workflow_id: str) -> RunTrace | None:
        """Load the golden trace or latest recorded run for a workflow."""
        wf = workflow_id.lower()
        for candidate in (
            self.golden_dir / f"golden_{wf}.json",
            self.trace_dir / f"latest_{wf}.json",
        ):
            if candidate.exists():
                return self.load_trace(candidate)
        return None

