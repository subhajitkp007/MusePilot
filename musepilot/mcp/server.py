# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Model Context Protocol (MCP) server implementation for MusePilot.

Allows AI coding assistants (Claude Desktop, Cursor, Antigravity, Cline)
to invoke MusePilot's visual perception (Meta SAM 3.1), multimodal planning
(Muse Spark), open-weight verification, and device actuation directly over
standard JSON-RPC transports (stdio and SSE).
"""

from __future__ import annotations

import base64
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal

from mcp.server.mcpserver import MCPServer

from musepilot.config import get_settings
from musepilot.contracts.schemas import WORKFLOWS, RunRequest, TraceSummary
from musepilot.eval.benchmark import BenchmarkEngine
from musepilot.execution.device import AdbDeviceDriver, get_device_driver
from musepilot.health.checker import run_health_check
from musepilot.orchestrator.agent_loop import MusePilotOrchestrator
from musepilot.telemetry.logger import get_logger
from musepilot.trace.recorder import TraceStore
from musepilot.voice.transcribe_client import MuseVoiceTranscribeClient

logger = get_logger("musepilot.mcp")


def create_mcp_server() -> MCPServer:
    """Construct and configure the official MusePilot MCP server."""
    server = MCPServer(
        name="musepilot",
        description=(
            "Multimodal visual automation infrastructure powered by Meta SAM 3.1 "
            "and Muse Spark. Execute UI workflows, verify ground truth with "
            "zero-coordinate receipts, self-heal UI obstacles, and query benchmark telemetry."
        ),
        version="0.1.0",
    )

    # -------------------------------------------------------------------------
    # MCP TOOLS
    # -------------------------------------------------------------------------

    @server.tool(
        description=(
            "Check MusePilot pre-flight system readiness, Meta API credentials, "
            "active visual perception model (SAM 3.1), multimodal planner (Muse Spark), "
            "verifier backend, and ADB device availability."
        )
    )
    def musepilot_health() -> dict[str, Any]:
        """Inspect pre-flight health and model readiness without leaking secrets."""
        report = run_health_check()
        return asdict(report)

    @server.tool(
        description=(
            "List available visual automation workflows with their step descriptions, "
            "default natural language intents, and target interface types."
        )
    )
    def musepilot_list_workflows() -> dict[str, Any]:
        """List executable workflow definitions."""
        return {"workflows": [w.model_dump() for w in WORKFLOWS]}

    @server.tool(
        description=(
            "Execute an autonomous visual automation workflow using Meta SAM 3.1 visual grounding "
            "and Muse Spark planning. Returns the full execution trace including step plan DAG, "
            "SAM 3.1 centroid hit rate, verifier pass/fail verdicts, and self-healing replan logs."
        )
    )
    def musepilot_execute_workflow(
        workflow_id: str = "w1",
        driver: Literal["simulated", "desktop", "adb"] = "simulated",
        inject_modal: bool = False,
        custom_intent: str | None = None,
    ) -> dict[str, Any]:
        """Execute a workflow and return the complete audit trace."""
        req = RunRequest(
            workflow_id=workflow_id,
            driver=driver,
            inject_modal=inject_modal,
            custom_intent=custom_intent,
        )
        device_driver = get_device_driver(req.driver)
        orchestrator = MusePilotOrchestrator(device_driver=device_driver)
        trace = orchestrator.run_workflow(
            workflow_id=req.workflow_id,
            custom_intent=req.custom_intent,
            inject_modal_obstruction=req.inject_modal,
            use_voice_intake=(req.workflow_id == "w2"),
        )
        return trace.model_dump(mode="json")

    @server.tool(
        description=(
            "List recent run-trace summaries from the local audit ledger (newest first). "
            "Returns trace IDs, workflow IDs, execution status, step counts, and pass rates."
        )
    )
    def musepilot_list_traces(limit: int = 10) -> dict[str, Any]:
        """List historical trace summaries."""
        bounded_limit = max(1, min(limit, 50))
        store = TraceStore()
        files = sorted(
            store.trace_dir.glob("trace_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:bounded_limit]
        summaries: list[dict[str, Any]] = []
        for path in files:
            try:
                trace = store.load_trace(path)
            except (OSError, ValueError):
                continue
            summaries.append(
                TraceSummary(
                    trace_id=trace.trace_id,
                    workflow_id=trace.workflow_id,
                    status=trace.status,
                    created_at=trace.created_at,
                    steps_completed=trace.metrics.total_steps_completed,
                    steps_planned=trace.metrics.total_steps_planned,
                    verification_pass_rate=trace.metrics.verification_pass_rate,
                    self_healing_recoveries=trace.metrics.self_healing_recoveries,
                ).model_dump()
            )
        return {"traces": summaries, "count": len(summaries)}

    @server.tool(
        description=(
            "Retrieve the full execution trace and verifier audit receipts for a specific trace ID, "
            "or pass 'latest' as trace_id to fetch the most recent trace for the given workflow."
        )
    )
    def musepilot_get_trace(trace_id: str, workflow_id: str = "w1") -> dict[str, Any]:
        """Fetch a specific execution trace by ID or latest."""
        store = TraceStore()
        if trace_id.lower() == "latest":
            trace = store.load_golden_or_latest(workflow_id)
            if trace is None:
                return {"error": f"No trace found for workflow '{workflow_id}'."}
            return trace.model_dump(mode="json")

        trace = store.find_trace(trace_id)
        if trace is None:
            return {"error": f"Trace '{trace_id}' not found."}
        return trace.model_dump(mode="json")

    @server.tool(
        description=(
            "Query cumulative quantitative reliability benchmarks across all recorded traces. "
            "Returns total runs analyzed, mean mask hit rate (100% zero-coordinate target), "
            "verification pass rate, self-healing success rate, and p50 inference latencies."
        )
    )
    def musepilot_get_benchmarks() -> dict[str, Any]:
        """Calculate and return cumulative reliability benchmarks."""
        engine = BenchmarkEngine()
        report = engine.evaluate_traces()
        return asdict(report)

    @server.tool(
        description=(
            "Probe and list connected hardware targets, including attached Android ADB devices "
            "(with serial numbers and connection status) and host desktop display configuration."
        )
    )
    def musepilot_list_devices() -> dict[str, Any]:
        """Discover connected devices and display capabilities."""
        settings = get_settings()
        adb_devices = AdbDeviceDriver.list_devices()
        return {
            "adb_available": len(adb_devices) > 0,
            "adb_devices": adb_devices,
            "preferred_adb_serial": settings.adb_serial
            or (adb_devices[0] if adb_devices else None),
            "display_dpi_scale": settings.display_dpi_scale,
            "execution_mode": settings.execution_mode,
            "allow_live_input": settings.allow_live_input,
        }

    @server.tool(
        description=(
            "Transcribe spoken operator audio into text intent using Meta Muse Voice Transcribe. "
            "Accepts either a base64-encoded WAV audio string or a local filesystem path to a WAV file."
        )
    )
    def musepilot_transcribe_voice(
        audio_base64: str | None = None,
        file_path: str | None = None,
        workflow_id: str = "w2",
    ) -> dict[str, Any]:
        """Transcribe operator speech into intent text."""
        wav_bytes: bytes
        if audio_base64:
            try:
                wav_bytes = base64.b64decode(audio_base64)
            except Exception as exc:
                return {"error": f"Invalid base64 audio payload: {exc}"}
        elif file_path:
            p = Path(file_path).expanduser().resolve()
            if not p.is_file():
                return {"error": f"Audio file not found: {file_path}"}
            wav_bytes = p.read_bytes()
        else:
            return {"error": "Either audio_base64 or file_path must be provided."}

        client = MuseVoiceTranscribeClient()
        try:
            record = client.transcribe_command(audio_bytes=wav_bytes, workflow_id=workflow_id)
            return {"transcript": record.text, "workflow_id": workflow_id}
        except Exception as exc:
            return {"error": f"Voice transcription failed: {exc}"}

    # -------------------------------------------------------------------------
    # MCP RESOURCES
    # -------------------------------------------------------------------------

    @server.resource("musepilot://health")
    def resource_health() -> str:
        """Real-time system health and driver availability report."""
        return json.dumps(asdict(run_health_check()), indent=2)

    @server.resource("musepilot://workflows")
    def resource_workflows() -> str:
        """Executable workflow catalogue."""
        return json.dumps([w.model_dump() for w in WORKFLOWS], indent=2)

    @server.resource("musepilot://benchmarks")
    def resource_benchmarks() -> str:
        """Cumulative quantitative reliability benchmarks and MTTR metrics."""
        report = BenchmarkEngine().evaluate_traces()
        return json.dumps(asdict(report), indent=2)

    @server.resource("musepilot://traces/latest")
    def resource_latest_trace() -> str:
        """Latest execution trace from the local audit ledger."""
        store = TraceStore()
        trace = store.load_golden_or_latest("w1")
        if trace is None:
            return json.dumps({"error": "No traces available"})
        return trace.model_dump_json(indent=2)

    @server.resource("musepilot://devices")
    def resource_devices() -> str:
        """Hardware devices and display status."""
        devices = AdbDeviceDriver.list_devices()
        return json.dumps({"adb_devices": devices, "count": len(devices)}, indent=2)

    # -------------------------------------------------------------------------
    # MCP PROMPTS
    # -------------------------------------------------------------------------

    @server.prompt("visual_regression_audit")
    def prompt_visual_qa(workflow_id: str = "w1", driver: str = "simulated") -> str:
        """Prompt template for autonomous visual regression testing."""
        return (
            f"You are the autonomous Visual QA and visual regression testing auditor using MusePilot.\n\n"
            f"Task: Execute workflow '{workflow_id}' on driver '{driver}'.\n"
            f"1. Use `musepilot_execute_workflow` to run the scenario.\n"
            f"2. Inspect the returned step execution records.\n"
            f"3. Verify that 100% of steps met the zero-coordinate invariant (hit rate = 1.0).\n"
            f"4. Confirm that the open-weight Spark verifier passed each visual assertion.\n"
            f"5. Summarize the audit result with execution time, pass rate, and receipt IDs."
        )

    @server.prompt("self_healing_recovery_test")
    def prompt_self_healing_test(driver: str = "simulated") -> str:
        """Prompt template for testing dynamic replanning when an unexpected obstacle appears."""
        return (
            f"You are evaluating MusePilot's self-healing autonomy under unexpected UI anomalies.\n\n"
            f"Task: Test self-healing obstacle recovery on driver '{driver}'.\n"
            f"1. Call `musepilot_execute_workflow` with `workflow_id='w2'` and `inject_modal=True`.\n"
            f"2. Observe how SAM 3.1 detects the unexpected blocker modal.\n"
            f"3. Check the replan log to verify Muse Spark generated a dynamic recovery step to dismiss it.\n"
            f"4. Verify that execution resumed and all subsequent goals were achieved.\n"
            f"5. Report the MTTR (Mean Time to Recovery) and replan receipt."
        )

    return server


def run_mcp_server(
    transport: Literal["stdio", "sse", "streamable-http"] = "stdio", **kwargs: Any
) -> None:
    """Run the MusePilot MCP server."""
    server = create_mcp_server()
    server.run(transport=transport, **kwargs)
