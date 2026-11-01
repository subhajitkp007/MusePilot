# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Command-line interface for running, replaying, and verifying MusePilot workflows."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from musepilot.contracts.schemas import LiveModelError
from musepilot.eval.benchmark import BenchmarkEngine
from musepilot.execution.device import get_device_driver
from musepilot.health.checker import run_health_check
from musepilot.orchestrator import MusePilotOrchestrator
from musepilot.trace import TraceStore


def build_parser() -> argparse.ArgumentParser:
    """Build the MusePilot CLI argument parser."""
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
    run_p.add_argument(
        "--pause-after",
        type=int,
        default=None,
        help="Pause the run after N verified steps for later resume",
    )
    run_p.add_argument(
        "--voice-audio",
        type=Path,
        default=None,
        help="WAV file with a spoken command (required for live voice intake)",
    )
    run_p.add_argument(
        "--driver",
        choices=["simulated", "desktop", "adb"],
        default="simulated",
        help="Target device driver: simulated, desktop, or adb (Android)",
    )
    run_p.add_argument(
        "--adb-serial",
        type=str,
        default=None,
        help="Optional target Android device ADB serial",
    )

    # `resume` command
    res_p = sub.add_parser("resume", help="Resume a paused workflow trace")
    res_p.add_argument(
        "--trace-id",
        type=str,
        required=True,
        help="Trace ID of the paused run to resume",
    )
    res_p.add_argument(
        "--intent",
        type=str,
        default=None,
        help="Optional new intent to re-target the remaining steps",
    )
    res_p.add_argument(
        "--voice-audio",
        type=Path,
        default=None,
        help="Optional audio file with a spoken re-target command",
    )
    res_p.add_argument(
        "--pause-after",
        type=int,
        default=None,
        help="Pause again after reaching the given original step position",
    )
    res_p.add_argument(
        "--driver",
        choices=["simulated", "desktop", "adb"],
        default="simulated",
        help="Target device driver: simulated, desktop, or adb (Android)",
    )
    res_p.add_argument(
        "--adb-serial",
        type=str,
        default=None,
        help="Optional target Android device ADB serial",
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

    # `eval` command
    ev_p = sub.add_parser(
        "eval", help="Run quantitative evaluation benchmark over historical traces"
    )
    ev_p.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output report format (markdown or json)",
    )
    ev_p.add_argument(
        "--save",
        type=Path,
        default=None,
        help="Optional file path to persist JSON benchmark report",
    )

    # `health` command
    sub.add_parser("health", help="Run pre-flight calibration and compliance checks")

    # `mcp` command
    mcp_p = sub.add_parser(
        "mcp",
        help="Run the Model Context Protocol (MCP) server for Claude Desktop, Cursor, and agent frameworks",
    )
    mcp_p.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport protocol: stdio (for Cursor/Claude Desktop) or sse (default: stdio)",
    )
    mcp_p.add_argument(
        "--port",
        type=int,
        default=8502,
        help="Port for SSE transport (default: 8502)",
    )

    # `jwt-token` command
    jwt_p = sub.add_parser(
        "jwt-token", help="Generate an enterprise HS256 JWT for API authentication"
    )
    jwt_p.add_argument("--subject", "-s", default="operator", help="Subject claim (sub) for token")
    jwt_p.add_argument(
        "--hours", type=int, default=24, help="Token validity lifetime in hours (default: 24)"
    )
    jwt_p.add_argument(
        "--secret",
        default=None,
        help="Secret HMAC key (defaults to MUSEPILOT_JWT_SECRET from config)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Dispatch CLI commands and return the process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "health":
        report = run_health_check()
        print(json.dumps(asdict(report), indent=2))
        return 0 if report.passed else 1

    if args.command == "mcp":
        from musepilot.mcp.server import run_mcp_server

        try:
            run_mcp_server(
                transport=args.transport,
                port=args.port if args.transport == "sse" else None,
            )
        except KeyboardInterrupt:
            return 0
        return 0

    if args.command == "jwt-token":
        from musepilot.config import get_settings
        from musepilot.security import generate_jwt

        secret = (
            args.secret or get_settings().jwt_secret or "musepilot-dev-secret-change-in-production"
        )
        token = generate_jwt(
            payload={"sub": args.subject, "iss": "musepilot", "role": "operator"},
            secret=secret,
            expires_in_seconds=args.hours * 3600,
        )
        print("\n=== MusePilot Enterprise JWT Token ===")
        print(f"Subject:    {args.subject}")
        print(f"Expires in: {args.hours} hours")
        print(f"Token:\n{token}\n")
        print("To authenticate clients, pass header:")
        print(f"Authorization: Bearer {token}\n")
        print("Or configure in your .env file:")
        print(f"MUSEPILOT_JWT_SECRET={secret}")
        print(f"MUSEPILOT_JWT_TOKEN={token}\n")
        return 0

    if args.command == "run":
        driver = get_device_driver(args.driver, serial=args.adb_serial)
        orchestrator = MusePilotOrchestrator(device_driver=driver)
        try:
            trace = orchestrator.run_workflow(
                workflow_id=args.workflow,
                custom_intent=args.intent,
                use_voice_intake=(args.workflow == "w2"),
                inject_modal_obstruction=args.inject_modal,
                save_as_golden=True,
                pause_after_step=args.pause_after,
                voice_audio=args.voice_audio,
            )
        except LiveModelError as exc:
            print(f"Live model error: {exc}", file=sys.stderr)
            return 2
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

    if args.command == "resume":
        driver = get_device_driver(args.driver, serial=args.adb_serial)
        orchestrator = MusePilotOrchestrator(device_driver=driver)
        trace = orchestrator.resume_workflow(
            trace_id=args.trace_id,
            new_intent=args.intent,
            voice_audio=args.voice_audio,
            pause_after_step=args.pause_after,
        )
        summary = {
            "mode": "RESUME",
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

    if args.command == "eval":
        engine = BenchmarkEngine()
        report = engine.evaluate_traces()
        if args.save is not None:
            args.save.parent.mkdir(parents=True, exist_ok=True)
            args.save.write_text(report.to_json(), encoding="utf-8")
        if args.format == "json":
            print(report.to_json())
        else:
            print(report.to_markdown_table())
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
