# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Focused tests for retry budget, escalation halt, and pause/resume/re-target."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from musepilot.orchestrator import MusePilotOrchestrator
from musepilot.planning import MuseSparkPlanner
from musepilot.trace import TraceStore
from musepilot.verification import SparkOpenVerifier


def test_retry_recovers_from_transient_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prove a non-obstruction failure retries the same step without self-healing."""
    monkeypatch.setenv("MUSEPILOT_MAX_RETRIES_PER_STEP", "2")
    calls = {"count": 0}
    real_verify = SparkOpenVerifier.verify_transition

    def flaky_verify(self: Any, *args: Any, **kwargs: Any) -> Any:
        calls["count"] += 1
        verdict = real_verify(self, *args, **kwargs)
        if calls["count"] == 1:
            return verdict.model_copy(
                update={
                    "passed": False,
                    "obstruction_detected": False,
                    "observed_change": "Transient render glitch",
                    "retry_hint": "Retry the same step.",
                }
            )
        return verdict

    monkeypatch.setattr(SparkOpenVerifier, "verify_transition", flaky_verify)
    store = TraceStore(trace_dir=tmp_path)
    trace = MusePilotOrchestrator(trace_store=store).run_workflow(
        workflow_id="w1", use_voice_intake=False, save_as_golden=False
    )

    assert trace.status == "COMPLETED"
    step_records = [r for r in trace.records if r.step.step_id == 1]
    assert [r.attempt_number for r in step_records] == [1, 2]
    assert not any(r.self_healed for r in step_records)
    assert trace.metrics.self_healing_recoveries == 0


def test_retry_exhaustion_halts_with_escalation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prove exhausted retries halt the run with ESCALATED status."""
    monkeypatch.setenv("MUSEPILOT_MAX_RETRIES_PER_STEP", "1")
    real_verify = SparkOpenVerifier.verify_transition

    def always_fail(self: Any, *args: Any, **kwargs: Any) -> Any:
        verdict = real_verify(self, *args, **kwargs)
        return verdict.model_copy(
            update={
                "passed": False,
                "obstruction_detected": False,
                "observed_change": "Persistent failure",
                "retry_hint": "Retry the same step.",
            }
        )

    monkeypatch.setattr(SparkOpenVerifier, "verify_transition", always_fail)
    store = TraceStore(trace_dir=tmp_path)
    trace = MusePilotOrchestrator(trace_store=store).run_workflow(
        workflow_id="w1", use_voice_intake=False, save_as_golden=False
    )

    assert trace.status == "ESCALATED"
    step_records = [r for r in trace.records if r.step.step_id == 1]
    assert [r.attempt_number for r in step_records] == [1, 2]
    assert not any(r.step.step_id == 2 for r in trace.records)


def test_pause_and_resume_completes_workflow(tmp_path: Path) -> None:
    """Prove a paused run resumes to completion under the same trace ID."""
    store = TraceStore(trace_dir=tmp_path)
    orchestrator = MusePilotOrchestrator(trace_store=store)

    paused = orchestrator.run_workflow(
        workflow_id="w1", use_voice_intake=False, pause_after_step=2, save_as_golden=False
    )
    assert paused.status == "PAUSED"
    assert len(paused.records) == 2
    assert paused.resume_state_label is not None

    resumed = orchestrator.resume_workflow(paused.trace_id)
    assert resumed.trace_id == paused.trace_id
    assert resumed.status == "COMPLETED"
    assert len(resumed.records) == 4
    assert resumed.metrics.total_steps_completed == 4


def test_resume_rejects_non_paused_trace(tmp_path: Path) -> None:
    """Prove resume refuses traces that are not paused."""
    store = TraceStore(trace_dir=tmp_path)
    orchestrator = MusePilotOrchestrator(trace_store=store)
    trace = orchestrator.run_workflow(
        workflow_id="w1", use_voice_intake=False, save_as_golden=False
    )

    with pytest.raises(ValueError, match="not paused"):
        orchestrator.resume_workflow(trace.trace_id)


def test_resume_with_new_intent_replans_remaining(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prove resume with a new intent replans the remaining steps."""
    captured: dict[str, Any] = {}
    real_plan = MuseSparkPlanner.plan_workflow

    def spying_plan(self: Any, *args: Any, **kwargs: Any) -> Any:
        captured["intent"] = kwargs.get("intent", args[1] if len(args) > 1 else None)
        captured["replan_reason"] = kwargs.get("replan_reason")
        return real_plan(self, *args, **kwargs)

    monkeypatch.setattr(MuseSparkPlanner, "plan_workflow", spying_plan)
    store = TraceStore(trace_dir=tmp_path)
    orchestrator = MusePilotOrchestrator(trace_store=store)
    paused = orchestrator.run_workflow(
        workflow_id="w1", use_voice_intake=False, pause_after_step=1, save_as_golden=False
    )

    resumed = orchestrator.resume_workflow(paused.trace_id, new_intent="Finish urgently")

    assert resumed.status == "COMPLETED"
    assert len(resumed.records) == 4
    assert captured["intent"] == "Finish urgently"
    assert captured["replan_reason"] is not None


def test_cli_pause_and_resume() -> None:
    """Prove the CLI pause-after and resume commands round-trip a workflow."""
    from musepilot.cli import main as cli_main

    assert cli_main(["run", "--workflow", "w1", "--pause-after", "1"]) == 0
    store = TraceStore()
    paused = store.load_golden_or_latest("w1")
    assert paused is not None and paused.status == "PAUSED"
    assert cli_main(["resume", "--trace-id", paused.trace_id]) == 0
    resumed = store.load_trace(store.trace_dir / f"trace_w1_{paused.trace_id}.json")
    assert resumed.status == "COMPLETED"
    assert len(resumed.records) == 4
