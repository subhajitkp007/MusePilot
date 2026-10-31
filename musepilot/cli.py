# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Command-line interface for running, replaying, and verifying MusePilot workflows."""

from __future__ import annotations

import argparse
import json
import sys

from musepilot.health.checker import run_health_check
from musepilot.orchestrator import MusePilotOrchestrator
from musepilot.trace import TraceStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="musepilot",
        description="MusePilot: Zero-Coordinate, Visually-Verified Multimodal GUI Agent",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # `run` command
    run_p = sub.add_parser("run", help="Execute a closed-loop workflow (W1 or W2)")
    run_p.add_argument(
        "--workflow",
        choices=["w1", "w2"],
        default="w1",
        help="Target frozen workflow ID (w1: Precision Canvas, w2: Voice + Self-Healing)",
    )
    run_p.add_argument(
        "--inject-modal",
        action="store_true",
        help="Inject a transient blocking modal on W2 Step 2 to demonstrate self-healing",
    )
    run_p.add_argument(
        "--intent",
        type=str,
        default=None,
        help="Optional custom operator intent string",
    )

    # `replay` command
    rep_p = sub.add_parser(
        "replay", help="Deterministically replay a golden or recorded workflow trace"
    )
    rep_p.add_argument(
        "--workflow",
        choices=["w1", "w2"],
        default="w1",
        help="Workflow ID to replay",
    )

    # `health` command
    sub.add_parser("health", help="Run pre-flight calibration and compliance checks")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "health":
        report = run_health_check()
        print(json.dumps(report.__dict__, indent=2))
        return 0 if report.passed else 1

    if args.command == "run":
        orchestrator = MusePilotOrchestrator()
        trace = orchestrator.run_workflow(
            workflow_id=args.workflow,
            custom_intent=args.intent,
            use_voice_intake=(args.workflow == "w2"),
            inject_modal_obstruction=args.inject_modal,
            save_as_golden=True,
        )
        summary = {
            "trace_id": trace.trace_id,
            "workflow_id": trace.workflow_id,
            "status": trace.status,
            "plan_summary": trace.plan.plan_summary,
            "records_executed": len(trace.records),
            "metrics": trace.metrics.model_dump(),
        }
        print(json.dumps(summary, indent=2))
        return 0

    if args.command == "replay":
        store = TraceStore()
        trace = store.load_golden_or_latest(args.workflow)
        if trace is None:
            orchestrator = MusePilotOrchestrator(trace_store=store)
            trace = orchestrator.run_workflow(
                workflow_id=args.workflow,
                use_voice_intake=(args.workflow == "w2"),
                inject_modal_obstruction=(args.workflow == "w2"),
                save_as_golden=True,
            )
        replay_summary = {
            "mode": "DETERMINISTIC_REPLAY",
            "trace_id": trace.trace_id,
            "workflow_id": trace.workflow_id,
            "status": trace.status,
            "steps": [
                {
                    "attempt": r.attempt_number,
                    "step_id": r.step.step_id,
                    "op": r.step.operation.value,
                    "target_mask_id": r.step.target_mask_id,
                    "os_logical_point": r.receipt.os_logical_point,
                    "verified": r.verdict.passed,
                    "self_healed": r.self_healed,
                    "observed_change": r.verdict.observed_change,
                }
                for r in trace.records
            ],
            "metrics": trace.metrics.model_dump(),
        }
        print(json.dumps(replay_summary, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())

