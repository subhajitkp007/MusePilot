# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""HTTP + WebSocket API serving run control, traces, frames, and benchmarks."""

from __future__ import annotations

import asyncio
import io
import json
import re
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocket, WebSocketDisconnect

from musepilot.config import get_settings
from musepilot.contracts.schemas import (
    LiveModelError,
    RunRequest,
    RunTrace,
    TraceSummary,
    VoiceTranscript,
    WorkflowInfo,
)
from musepilot.eval.benchmark import BenchmarkEngine
from musepilot.execution.device import get_device_driver
from musepilot.health.checker import run_health_check
from musepilot.orchestrator import MusePilotOrchestrator
from musepilot.perception import (
    SAM31PerceptionClient,
    ScreenCaptureEngine,
    SetOfMarkRenderer,
)
from musepilot.telemetry import GLOBAL_TELEMETRY, get_logger
from musepilot.trace import TraceStore
from musepilot.voice import MuseVoiceTranscribeClient

logger = get_logger("musepilot.server")

WORKFLOWS: tuple[WorkflowInfo, ...] = (
    WorkflowInfo(
        workflow_id="w1",
        title="W1: Precision Canvas Calibration",
        description="Calibrate frequency slider, damping toggle, gain input, and benchmark on a 0-DOM-node canvas.",
    ),
    WorkflowInfo(
        workflow_id="w2",
        title="W2: Voice Incident Dispatch + Self-Healing",
        description="Transcribe a spoken incident command and dispatch it across apps with modal recovery.",
    ),
)

_STATE_LABEL_RE = re.compile(r"^[A-Za-z0-9_]{1,64}$")
_WEB_DIR = Path(__file__).resolve().parent / "static" / "web"


def _error(message: str, status_code: int) -> JSONResponse:
    """Build a JSON error envelope without leaking server internals."""
    return JSONResponse({"detail": message}, status_code=status_code)


def _execute_run_blocking(request: RunRequest) -> RunTrace:
    """Run a workflow synchronously inside a worker thread."""
    driver = get_device_driver(request.driver)
    orchestrator = MusePilotOrchestrator(device_driver=driver)
    return orchestrator.run_workflow(
        workflow_id=request.workflow_id,
        custom_intent=request.custom_intent,
        use_voice_intake=(request.workflow_id == "w2" and request.custom_intent is None),
        inject_modal_obstruction=request.inject_modal,
        save_as_golden=False,
    )


def _resolve_trace(trace_id: str | None, workflow_id: str) -> RunTrace | None:
    """Load a trace by ID, falling back to the golden/latest workflow trace."""
    store = TraceStore()
    if trace_id:
        found = store.find_trace(trace_id)
        if found is not None:
            return found
    return store.load_golden_or_latest(workflow_id)


def _state_timeline(trace: RunTrace | None, workflow_id: str) -> list[str]:
    """Replicate the HUD visual-state timeline for a workflow and trace."""
    states = ["initial"]
    if workflow_id == "w2" and trace is not None and any(r.self_healed for r in trace.records):
        states.extend(["step_1", "step_2_modal_blocked", "step_2_recovered", "step_3_final"])
    elif trace is not None:
        for i in range(1, len(trace.plan.steps)):
            states.append(f"step_{i}")
        states.append(f"step_{len(trace.plan.steps)}_final")
    return states


def _active_target(trace: RunTrace | None, state_label: str) -> int:
    """Select the highlighted mask for a timeline state."""
    if "modal" in state_label:
        return 4
    if trace is not None and trace.records:
        return trace.records[-1].step.target_mask_id
    return 1


def _png_response(image: Any) -> Response:
    """Encode a PIL image as a PNG response."""
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return Response(buffer.getvalue(), media_type="image/png")


async def api_index(_request: Request) -> JSONResponse:
    """Describe the MusePilot HUD API surface."""
    return JSONResponse(
        {
            "service": "musepilot-api",
            "version": "0.1.0",
            "endpoints": [
                "GET /api/health",
                "GET /api/config",
                "GET /api/workflows",
                "POST /api/runs",
                "POST /api/voice/transcribe",
                "WS /ws/runs",
                "GET /api/traces",
                "GET /api/traces/latest/{workflow_id}",
                "GET /api/traces/{trace_id}",
                "GET /api/states",
                "GET /api/frames/raw",
                "GET /api/frames/som",
                "GET /api/benchmark",
                "GET /api/openapi.json",
            ],
        }
    )


def openapi_document() -> dict[str, Any]:
    """Build the OpenAPI document from routes and Pydantic contracts."""
    schemas: dict[str, Any] = {}
    for model in (RunRequest, RunTrace, TraceSummary, VoiceTranscript, WorkflowInfo):
        rendered = model.model_json_schema(ref_template="#/components/schemas/{model}")
        schemas.update(rendered.pop("$defs", {}))
        schemas[model.__name__] = rendered
    trace_ref = {"$ref": "#/components/schemas/RunTrace"}
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "MusePilot HUD API",
            "version": "0.1.0",
            "description": (
                "Run, inspect, and verify zero-coordinate GUI automation. "
                "Live WebSocket run streaming is available at /ws/runs."
            ),
        },
        "paths": {
            "/api/health": {
                "get": {
                    "operationId": "getHealth",
                    "summary": "Pre-flight readiness report",
                    "responses": {"200": {"description": "Readiness report"}},
                }
            },
            "/api/config": {
                "get": {
                    "operationId": "getConfig",
                    "summary": "Non-secret runtime configuration",
                    "responses": {"200": {"description": "Runtime configuration"}},
                }
            },
            "/api/workflows": {
                "get": {
                    "operationId": "listWorkflows",
                    "summary": "Frozen executable workflows",
                    "responses": {
                        "200": {
                            "description": "Workflow descriptors",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/WorkflowInfo"},
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/api/runs": {
                "post": {
                    "operationId": "createRun",
                    "summary": "Execute a workflow and return its trace",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/RunRequest"}
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Full run trace",
                            "content": {"application/json": {"schema": trace_ref}},
                        },
                        "400": {"description": "Invalid request"},
                        "502": {"description": "Live model call failed"},
                    },
                }
            },
            "/api/voice/transcribe": {
                "post": {
                    "operationId": "transcribeAudio",
                    "summary": "Transcribe a WAV command",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "multipart/form-data": {
                                "schema": {
                                    "type": "object",
                                    "required": ["audio"],
                                    "properties": {
                                        "audio": {
                                            "type": "string",
                                            "format": "binary",
                                            "description": "WAV audio file",
                                        },
                                        "workflow_id": {
                                            "type": "string",
                                            "enum": ["w1", "w2"],
                                            "default": "w2",
                                        },
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Voice transcript",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/VoiceTranscript"}
                                }
                            },
                        },
                        "400": {"description": "Invalid upload"},
                        "502": {"description": "Transcription failed"},
                    },
                }
            },
            "/api/traces": {
                "get": {
                    "operationId": "listTraces",
                    "summary": "Recent run-trace summaries",
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "schema": {"type": "integer", "default": 20},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Trace summaries",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/TraceSummary"},
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/api/traces/latest/{workflow_id}": {
                "get": {
                    "operationId": "getLatestTrace",
                    "summary": "Golden or latest trace for a workflow",
                    "parameters": [
                        {
                            "name": "workflow_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string", "enum": ["w1", "w2"]},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Full run trace",
                            "content": {"application/json": {"schema": trace_ref}},
                        },
                        "404": {"description": "No trace recorded yet"},
                    },
                }
            },
            "/api/traces/{trace_id}": {
                "get": {
                    "operationId": "getTrace",
                    "summary": "Single trace by ID",
                    "parameters": [
                        {
                            "name": "trace_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Full run trace",
                            "content": {"application/json": {"schema": trace_ref}},
                        },
                        "404": {"description": "Trace not found"},
                    },
                }
            },
            "/api/states": {
                "get": {
                    "operationId": "getStates",
                    "summary": "Visual-state timeline labels",
                    "parameters": [
                        {
                            "name": "workflow",
                            "in": "query",
                            "schema": {"type": "string", "default": "w1"},
                        },
                        {"name": "trace_id", "in": "query", "schema": {"type": "string"}},
                    ],
                    "responses": {"200": {"description": "Timeline labels"}},
                }
            },
            "/api/frames/raw": {
                "get": {
                    "operationId": "getRawFrame",
                    "summary": "Raw canvas frame PNG",
                    "parameters": [
                        {
                            "name": "workflow",
                            "in": "query",
                            "schema": {"type": "string", "default": "w1"},
                        },
                        {
                            "name": "state",
                            "in": "query",
                            "schema": {"type": "string", "default": "initial"},
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "PNG frame",
                            "content": {"image/png": {"schema": {"type": "string"}}},
                        }
                    },
                }
            },
            "/api/frames/som": {
                "get": {
                    "operationId": "getSomFrame",
                    "summary": "Set-of-Mark overlay PNG",
                    "parameters": [
                        {
                            "name": "workflow",
                            "in": "query",
                            "schema": {"type": "string", "default": "w1"},
                        },
                        {
                            "name": "state",
                            "in": "query",
                            "schema": {"type": "string", "default": "initial"},
                        },
                        {"name": "trace_id", "in": "query", "schema": {"type": "string"}},
                    ],
                    "responses": {
                        "200": {
                            "description": "PNG overlay",
                            "content": {"image/png": {"schema": {"type": "string"}}},
                        }
                    },
                }
            },
            "/api/benchmark": {
                "get": {
                    "operationId": "getBenchmark",
                    "summary": "Cumulative benchmark report",
                    "responses": {"200": {"description": "Benchmark report"}},
                }
            },
            "/api/openapi.json": {
                "get": {
                    "operationId": "getOpenApi",
                    "summary": "This OpenAPI document",
                    "responses": {"200": {"description": "OpenAPI JSON"}},
                }
            },
        },
        "components": {"schemas": schemas},
    }


async def get_openapi(_request: Request) -> JSONResponse:
    """Serve the machine-readable OpenAPI document."""
    return JSONResponse(openapi_document())


async def get_health(_request: Request) -> JSONResponse:
    """Return the pre-flight readiness report (no secret material)."""
    report = await run_in_threadpool(run_health_check)
    return JSONResponse(asdict(report))


async def get_config(_request: Request) -> JSONResponse:
    """Return non-secret runtime configuration for HUD clients."""
    settings = get_settings()
    return JSONResponse(
        {
            "execution_mode": settings.execution_mode,
            "display_dpi_scale": settings.display_dpi_scale,
            "sam_model_id": settings.sam_model_id,
            "planner_model_id": settings.planner_model_id,
            "verifier_model_id": settings.verifier_model_id,
            "verifier_backend": settings.verifier_backend,
            "meta_verifier_model_id": settings.meta_verifier_model_id,
            "voice_model_id": settings.voice_model_id,
            "partner_provider": settings.partner_provider,
        }
    )


async def list_workflows(_request: Request) -> JSONResponse:
    """List the frozen demo workflows."""
    return JSONResponse([w.model_dump() for w in WORKFLOWS])


async def create_run(request: Request) -> JSONResponse:
    """Execute a workflow synchronously and return its full trace."""
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return _error("Request body must be valid JSON.", 400)
    try:
        run_request = RunRequest.model_validate(payload)
    except ValidationError as exc:
        return _error(f"Invalid run request: {exc.errors()[0]['msg']}.", 400)
    if (
        get_settings().execution_mode == "live"
        and run_request.workflow_id == "w2"
        and run_request.custom_intent is None
    ):
        return _error(
            "Live W2 runs need transcribed intent: POST audio to /api/voice/transcribe, "
            "then pass the text as custom_intent.",
            400,
        )
    try:
        trace = await run_in_threadpool(_execute_run_blocking, run_request)
    except ValueError as exc:
        return _error(str(exc), 400)
    except LiveModelError as exc:
        logger.warning(f"Live model call failed: {exc}")
        return _error(str(exc), 502)
    except RuntimeError as exc:
        logger.warning(f"Workflow run failed: {exc}")
        return _error("Workflow execution failed.", 500)
    return JSONResponse(trace.model_dump(mode="json"))


async def transcribe_audio(request: Request) -> JSONResponse:
    """Transcribe an uploaded WAV command via Muse Voice Transcribe."""
    try:
        form = await request.form()
    except Exception:
        return _error("Request body must be multipart form data.", 400)
    upload = form.get("audio")
    workflow_id = form.get("workflow_id", "w2")
    if not isinstance(upload, UploadFile) or not upload.filename:
        return _error("Multipart field 'audio' with a WAV file is required.", 400)
    if not upload.filename.lower().endswith(".wav"):
        return _error("Voice transcribe requires a WAV file.", 400)
    if workflow_id not in ("w1", "w2"):
        return _error("Unknown workflow_id; expected 'w1' or 'w2'.", 400)
    try:
        with tempfile.TemporaryDirectory(prefix="musepilot_voice_") as tmpdir:
            audio_path = Path(tmpdir) / "command.wav"
            audio_path.write_bytes(await upload.read())
            transcript = await run_in_threadpool(
                MuseVoiceTranscribeClient().transcribe_command,
                workflow_id,
                audio_path,
            )
    except LiveModelError as exc:
        logger.warning(f"Voice transcribe failed: {exc}")
        return _error(str(exc), 502)
    except OSError as exc:
        logger.warning(f"Voice upload failed: {exc}")
        return _error("Could not process the uploaded audio.", 400)
    return JSONResponse(transcript.model_dump(mode="json"))


async def list_traces(request: Request) -> JSONResponse:
    """List recent run-trace summaries, newest first."""
    raw_limit = request.query_params.get("limit", "20")
    try:
        limit = int(raw_limit)
    except ValueError:
        return _error("Query parameter 'limit' must be an integer.", 400)
    if not 1 <= limit <= 50:
        return _error("Query parameter 'limit' must be between 1 and 50.", 400)
    store = TraceStore()
    files = sorted(
        store.trace_dir.glob("trace_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]
    summaries: list[dict[str, Any]] = []
    for path in files:
        try:
            trace = store.load_trace(path)
        except (OSError, ValueError):
            logger.warning(f"Skipping unreadable trace file: {path.name}")
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
    return JSONResponse(summaries)


async def get_latest_trace(request: Request) -> JSONResponse:
    """Return the golden or latest trace for a workflow."""
    workflow_id = request.path_params["workflow_id"].lower()
    if workflow_id not in ("w1", "w2"):
        return _error("Unknown workflow_id; expected 'w1' or 'w2'.", 404)
    trace = _resolve_trace(None, workflow_id)
    if trace is None:
        return _error(f"No trace recorded yet for workflow '{workflow_id}'.", 404)
    return JSONResponse(trace.model_dump(mode="json"))


async def get_trace(request: Request) -> JSONResponse:
    """Return a single trace by ID."""
    trace = TraceStore().find_trace(request.path_params["trace_id"])
    if trace is None:
        return _error("Trace not found.", 404)
    return JSONResponse(trace.model_dump(mode="json"))


async def get_states(request: Request) -> JSONResponse:
    """Return the visual-state timeline labels for a workflow and trace."""
    params = request.query_params
    workflow_id = params.get("workflow", "w1").lower()
    if workflow_id not in ("w1", "w2"):
        return _error("Unknown workflow; expected 'w1' or 'w2'.", 400)
    trace = _resolve_trace(params.get("trace_id"), workflow_id)
    states = _state_timeline(trace, workflow_id)
    return JSONResponse({"states": states, "default_state": states[-1]})


def _validated_frame_params(request: Request) -> tuple[str, str, str | None] | JSONResponse:
    """Validate shared frame query parameters."""
    params = request.query_params
    workflow_id = params.get("workflow", "w1").lower()
    state_label = params.get("state", "initial")
    if workflow_id not in ("w1", "w2"):
        return _error("Unknown workflow; expected 'w1' or 'w2'.", 400)
    if not _STATE_LABEL_RE.match(state_label):
        return _error("Invalid state label.", 400)
    return workflow_id, state_label, params.get("trace_id")


async def get_raw_frame(request: Request) -> Response | JSONResponse:
    """Render the raw canvas frame for a workflow state as PNG."""
    validated = _validated_frame_params(request)
    if isinstance(validated, JSONResponse):
        return validated
    workflow_id, state_label, _ = validated
    capture = ScreenCaptureEngine()
    frame = await run_in_threadpool(capture.render_canvas_state, workflow_id, state_label)
    return _png_response(frame.image)


async def get_som_frame(request: Request) -> Response | JSONResponse:
    """Render the SAM 3.1 Set-of-Mark overlay for a workflow state as PNG."""
    validated = _validated_frame_params(request)
    if isinstance(validated, JSONResponse):
        return validated
    workflow_id, state_label, trace_id = validated
    trace = _resolve_trace(trace_id, workflow_id)
    settings = get_settings()
    capture = ScreenCaptureEngine(dpi_scale=settings.display_dpi_scale)
    frame = await run_in_threadpool(capture.render_canvas_state, workflow_id, state_label)
    sam_client = SAM31PerceptionClient()
    mask_set = await run_in_threadpool(
        sam_client.segment_frame,
        frame,
        workflow_id,
        trace.trace_id if trace else "hud-preview",
    )
    verified_ids = (
        {r.step.target_mask_id for r in trace.records if r.verdict.passed} if trace else set()
    )
    overlay = SetOfMarkRenderer().render_som_overlay(
        base_image=frame.image,
        mask_set=mask_set,
        active_target_mask_id=_active_target(trace, state_label),
        verified_mask_ids=verified_ids,
    )
    return _png_response(overlay)


async def get_benchmark(_request: Request) -> JSONResponse:
    """Evaluate historical traces and return the benchmark report."""
    report = await run_in_threadpool(BenchmarkEngine().evaluate_traces)
    return JSONResponse(json.loads(report.to_json()))


async def stream_run_spans(websocket: WebSocket) -> None:
    """Stream live telemetry spans for a run, then send the final trace."""
    await websocket.accept()
    try:
        payload = await websocket.receive_json()
    except (json.JSONDecodeError, RuntimeError):
        await websocket.send_json({"type": "error", "detail": "Request must be valid JSON."})
        await websocket.close()
        return
    try:
        run_request = RunRequest.model_validate(payload)
    except ValidationError as exc:
        await websocket.send_json(
            {"type": "error", "detail": f"Invalid run request: {exc.errors()[0]['msg']}."}
        )
        await websocket.close()
        return
    lock: asyncio.Lock = websocket.app.state.run_lock
    if lock.locked():
        await websocket.send_json(
            {"type": "error", "detail": "Another run is already in progress."}
        )
        await websocket.close()
        return
    async with lock:
        await websocket.send_json({"type": "started", "workflow_id": run_request.workflow_id})
        sent_span_ids: set[str] = set()
        loop = asyncio.get_running_loop()
        future = loop.run_in_executor(None, _execute_run_blocking, run_request)
        try:
            while not future.done():
                await _drain_spans(websocket, sent_span_ids)
                await asyncio.sleep(0.05)
            await _drain_spans(websocket, sent_span_ids)
            trace = future.result()
        except WebSocketDisconnect:
            future.cancel()
            return
        except LiveModelError as exc:
            logger.warning(f"Streamed live model call failed: {exc}")
            await websocket.send_json({"type": "error", "detail": str(exc)})
            await websocket.close()
            return
        except (ValueError, RuntimeError) as exc:
            logger.warning(f"Streamed workflow run failed: {exc}")
            await websocket.send_json({"type": "error", "detail": "Workflow execution failed."})
            await websocket.close()
            return
        await websocket.send_json({"type": "complete", "trace": trace.model_dump(mode="json")})
        await websocket.close()


async def _drain_spans(websocket: WebSocket, sent_span_ids: set[str]) -> None:
    """Send newly completed telemetry spans over the socket."""
    for span in list(GLOBAL_TELEMETRY.spans):
        if span.span_id not in sent_span_ids:
            sent_span_ids.add(span.span_id)
            await websocket.send_json({"type": "span", "span": span.to_otel_dict()})


def create_app() -> Starlette:
    """Build the MusePilot HUD API application."""
    routes: list[Route | WebSocketRoute | Mount] = [
        Route("/api/health", get_health),
        Route("/api/config", get_config),
        Route("/api/workflows", list_workflows),
        Route("/api/runs", create_run, methods=["POST"]),
        Route("/api/voice/transcribe", transcribe_audio, methods=["POST"]),
        Route("/api/traces", list_traces),
        Route("/api/traces/latest/{workflow_id}", get_latest_trace),
        Route("/api/traces/{trace_id}", get_trace),
        Route("/api/states", get_states),
        Route("/api/frames/raw", get_raw_frame),
        Route("/api/frames/som", get_som_frame),
        Route("/api/benchmark", get_benchmark),
        Route("/api/openapi.json", get_openapi),
        WebSocketRoute("/ws/runs", stream_run_spans),
    ]
    if (_WEB_DIR / "index.html").exists():
        routes.append(Mount("/", StaticFiles(directory=_WEB_DIR, html=True), name="hud-web"))
    else:
        routes.append(Route("/", api_index))
    app = Starlette(routes=routes)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.state.run_lock = asyncio.Lock()
    return app


app = create_app()


def main() -> None:
    """Launch the API server with uvicorn."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        app,
        host=settings.server_host,
        port=settings.server_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
