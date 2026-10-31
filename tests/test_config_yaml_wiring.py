# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Focused tests for YAML-backed configuration wiring and precedence."""

from __future__ import annotations

from pathlib import Path

import pytest

from musepilot.config import MusePilotSettings
from musepilot.orchestrator import MusePilotOrchestrator
from musepilot.trace import TraceStore


def test_yaml_file_provides_defaults_and_env_overrides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prove precedence: explicit init > env > YAML file > built-in defaults."""
    yaml_path = tmp_path / "custom.yaml"
    yaml_path.write_text(
        "models:\n"
        "  planner:\n"
        "    temperature: 0.0\n"
        "  verifier:\n"
        "    min_roi_pixel_delta: 0.5\n"
        "execution:\n"
        "  display_dpi_scale: 1.0\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("MUSEPILOT_CONFIG_YAML_PATH", str(yaml_path))
    monkeypatch.setenv("MUSEPILOT_DISPLAY_DPI_SCALE", "3.0")

    settings = MusePilotSettings()

    assert settings.config_yaml_path == yaml_path
    assert settings.planner_temperature == 0.0
    assert settings.verifier_min_roi_pixel_delta == 0.5
    assert settings.display_dpi_scale == 3.0
    assert settings.sam_model_id == "meta-models/sam-3.1"


def test_missing_yaml_falls_back_to_builtin_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prove a missing YAML file degrades gracefully to built-in defaults."""
    monkeypatch.setenv("MUSEPILOT_CONFIG_YAML_PATH", str(tmp_path / "does_not_exist.yaml"))

    settings = MusePilotSettings()

    assert settings.planner_temperature == 0.1
    assert settings.verifier_min_roi_pixel_delta == 0.015
    assert settings.allow_replan_on_obstruction is True


def test_replan_disabled_escalates_instead_of_self_healing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prove allow_replan_on_obstruction=false halts with ESCALATED status."""
    monkeypatch.setenv("MUSEPILOT_ALLOW_REPLAN_ON_OBSTRUCTION", "false")
    store = TraceStore(trace_dir=tmp_path)
    orchestrator = MusePilotOrchestrator(trace_store=store)

    trace = orchestrator.run_workflow(
        workflow_id="w2",
        use_voice_intake=True,
        inject_modal_obstruction=True,
        save_as_golden=False,
    )

    assert trace.status == "ESCALATED"
    assert trace.metrics.self_healing_recoveries == 0
    assert any(r.verdict.obstruction_detected for r in trace.records)
    assert not any(r.self_healed for r in trace.records)
