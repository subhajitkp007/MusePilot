# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Unit tests for quantitative evaluation benchmark engine (Milestone M9)."""

from __future__ import annotations

from pathlib import Path

from musepilot.eval.benchmark import BenchmarkEngine


def test_benchmark_engine_empty_directory(tmp_path: Path) -> None:
    engine = BenchmarkEngine(trace_dirs=[tmp_path])
    report = engine.evaluate_traces()
    assert report.total_runs_analyzed == 0
    assert report.total_steps_executed == 0
    assert "Verified Rehearsal Benchmark Report" in report.to_markdown_table()


def test_benchmark_engine_evaluates_historical_traces() -> None:
    project_root = Path(__file__).resolve().parent.parent
    real_dirs = [project_root / "traces", project_root / "demo" / "golden_traces"]
    engine = BenchmarkEngine(trace_dirs=real_dirs)
    report = engine.evaluate_traces()
    assert report.total_runs_analyzed >= 2
    assert report.mean_mask_hit_rate == 1.0
    assert report.self_healing_success_rate == 1.0
    assert "w1" in report.workflows
    assert "w2" in report.workflows
    md = report.to_markdown_table()
    assert "Mask Centroid Hit Rate" in md
    assert "Closed-Loop Verification Pass Rate" in md
