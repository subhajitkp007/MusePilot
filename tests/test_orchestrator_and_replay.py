# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Integration tests for closed-loop orchestration, self-healing, replay, and health check."""

from __future__ import annotations

from pathlib import Path

from musepilot.cli import main as cli_main
from musepilot.health.checker import run_health_check
from musepilot.orchestrator import MusePilotOrchestrator
from musepilot.trace import TraceStore


def test_pre_flight_health_check_passes() -> None:
    report = run_health_check()
    assert report.passed is True
    assert report.verifier_model_id == "meta-models/muse-spark-open-1026"


def test_workflow_w1_executes_and_verifies_end_to_end(tmp_path: Path) -> None:
    store = TraceStore(trace_dir=tmp_path)
    orchestrator = MusePilotOrchestrator(trace_store=store)
    trace = orchestrator.run_workflow(
        workflow_id="w1",
        use_voice_intake=False,
        inject_modal_obstruction=False,
        save_as_golden=False,
    )
    assert trace.status == "COMPLETED"
    assert trace.metrics.total_steps_planned == 4
    assert trace.metrics.total_steps_completed == 4
    assert trace.metrics.mask_centroid_hit_rate == 1.0
    assert trace.metrics.verification_pass_rate == 1.0


def test_workflow_w2_self_heals_from_injected_modal_obstruction(tmp_path: Path) -> None:
    store = TraceStore(trace_dir=tmp_path)
    orchestrator = MusePilotOrchestrator(trace_store=store)
    trace = orchestrator.run_workflow(
        workflow_id="w2",
        use_voice_intake=True,
        inject_modal_obstruction=True,
        save_as_golden=False,
    )
    assert trace.status == "COMPLETED"
    assert trace.voice_intake is not None
    assert trace.metrics.self_healing_recoveries == 1
    assert any(r.verdict.obstruction_detected for r in trace.records)
    assert any(r.self_healed and r.step.target_mask_id == 4 for r in trace.records)


def test_cli_run_and_deterministic_replay() -> None:
    assert cli_main(["health"]) == 0
    assert cli_main(["run", "--workflow", "w1"]) == 0
    assert cli_main(["run", "--workflow", "w2", "--inject-modal"]) == 0
    assert cli_main(["replay", "--workflow", "w1"]) == 0
    assert cli_main(["replay", "--workflow", "w2"]) == 0


def test_committed_golden_traces_validate_against_strict_schemas() -> None:
    store = TraceStore()
    golden_root = Path(__file__).resolve().parent.parent / "demo" / "golden_traces"
    for workflow_id in ("w1", "w2"):
        trace = store.load_trace(golden_root / f"golden_{workflow_id}.json")
        assert trace.workflow_id == workflow_id
        assert trace.metrics.total_steps_completed >= 1
