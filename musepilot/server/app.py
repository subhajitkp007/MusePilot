# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""HTTP + WebSocket API serving run control, traces, frames, and benchmarks."""

from __future__ import annotations

import asyncio
import hmac
import io
import json
import re
import subprocess
import tempfile
import threading
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from PIL import Image
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
    WORKFLOWS,
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
from musepilot.orchestrator import GLOBAL_RECORD_BUFFER, MusePilotOrchestrator
from musepilot.perception import (
    GLOBAL_FRAME_BUFFER,
    SAM31PerceptionClient,
    ScreenCaptureEngine,
    SetOfMarkRenderer,
)
from musepilot.security import (
    GLOBAL_RATE_LIMITER,
    JWTError,
    RateLimitMiddleware,
    decode_and_verify_jwt,
)
from musepilot.telemetry import GLOBAL_TELEMETRY, get_logger
from musepilot.trace import TraceStore
from musepilot.voice import MuseVoiceTranscribeClient

logger = get_logger("musepilot.server")

_STATE_LABEL_RE = re.compile(r"^[A-Za-z0-9_]{1,64}$")
_TRACE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_WEB_DIR = Path(__file__).resolve().parent / "static" / "web"


class SecurityHeadersMiddleware:
    """Inject Meta-standard enterprise security headers into all HTTP responses."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_security_headers(message: Any) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                header_names = {h[0].lower() for h in headers}
                if b"x-content-type-options" not in header_names:
                    headers.append((b"x-content-type-options", b"nosniff"))
                if b"x-frame-options" not in header_names:
                    headers.append((b"x-frame-options", b"SAMEORIGIN"))
                if b"referrer-policy" not in header_names:
                    headers.append((b"referrer-policy", b"strict-origin-when-cross-origin"))
                if b"permissions-policy" not in header_names:
                    headers.append(
                        (
                            b"permissions-policy",
                            b"accelerometer=(), camera=(), geolocation=(), gyroscope=(), payment=(), microphone=(self)",
                        )
                    )
                if b"x-xss-protection" not in header_names:
                    headers.append((b"x-xss-protection", b"1; mode=block"))
                if b"content-security-policy" not in header_names:
                    csp = (
                        b"default-src 'self'; "
                        b"script-src 'self' 'unsafe-eval' 'wasm-unsafe-eval' 'unsafe-inline' https://www.gstatic.com; "
                        b"style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                        b"img-src 'self' data: blob: https://www.gstatic.com; "
                        b"connect-src 'self' blob: data: ws: wss: http://localhost:* http://127.0.0.1:* ws://localhost:* ws://127.0.0.1:* https://www.gstatic.com https://fonts.gstatic.com; "
                        b"font-src 'self' data: https://fonts.gstatic.com; "
                        b"media-src 'self' blob: data:; "
                        b"worker-src 'self' blob:;"
                    )
                    headers.append((b"content-security-policy", csp))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_security_headers)


class JWTSessionCookieMiddleware:
    """Issue HttpOnly session JWT cookie so browsers loading the HUD need zero manual token knowledge."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        from musepilot.security import generate_jwt

        request = Request(scope)
        settings = getattr(request.app.state, "settings", None) or get_settings()
        jwt_sec = getattr(settings, "jwt_secret", "")
        jwt_tok = getattr(settings, "jwt_token", "")

        path = scope.get("path", "")
        is_ui_entrypoint = path in ("/", "/index.html", "/api/auth/token")
        has_cookie = "musepilot_jwt" in request.cookies

        async def send_with_session_cookie(message: Any) -> None:
            if message["type"] == "http.response.start":
                if is_ui_entrypoint and not has_cookie and (jwt_sec or jwt_tok):
                    token_to_set = jwt_tok
                    if not token_to_set and jwt_sec:
                        token_to_set = generate_jwt(
                            payload={"sub": "hud-operator", "role": "operator", "iss": "musepilot"},
                            secret=jwt_sec,
                            expires_in_seconds=86400 * 30,
                        )
                    if token_to_set:
                        headers = list(message.get("headers", []))
                        cookie_hdr = f"musepilot_jwt={token_to_set}; Path=/; SameSite=Lax; HttpOnly"
                        headers.append((b"set-cookie", cookie_hdr.encode("latin1")))
                        message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_session_cookie)


def _extract_token(
    headers: Any,
    query_params: Any,
    cookies: dict[str, str] | None = None,
) -> str | None:
    """Extract bearer/api-key/query/cookie token."""
    auth_header = headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    api_key = headers.get("x-api-key", "").strip()
    if api_key:
        return api_key
    query_token = query_params.get("token", "").strip()
    if query_token:
        return query_token
    if cookies and "musepilot_jwt" in cookies:
        return cookies["musepilot_jwt"].strip()
    return None


def _is_token_authorized(token: str | None, settings: Any) -> bool:
    """Validate token against configured JWT or API token settings."""
    has_auth_configured = bool(
        getattr(settings, "api_token", "")
        or getattr(settings, "jwt_secret", "")
        or getattr(settings, "jwt_token", "")
    )
    if not has_auth_configured:
        return True  # Dev mode: open

    if not token:
        return False

    # 1. Exact match against static JWT token from .env
    jwt_tok = getattr(settings, "jwt_token", "")
    if jwt_tok and hmac.compare_digest(token, jwt_tok.strip()):
        return True

    # 2. Exact match against API token from .env
    api_tok = getattr(settings, "api_token", "")
    if api_tok and hmac.compare_digest(token, api_tok.strip()):
        return True

    # 3. Cryptographic signature verification via JWT secret from .env
    jwt_sec = getattr(settings, "jwt_secret", "")
    if jwt_sec:
        try:
            decode_and_verify_jwt(
                token,
                secret=jwt_sec,
                allowed_algorithms=(getattr(settings, "jwt_algorithm", "HS256"),),
            )
            return True
        except JWTError as exc:
            logger.debug(f"JWT verification rejected: {exc}")

    return False


def _verify_auth(request: Request) -> bool:
    """Verify request authorization against JWT or API token configuration."""
    settings = getattr(request.app.state, "settings", None) or get_settings()
    token = _extract_token(request.headers, request.query_params, request.cookies)
    return _is_token_authorized(token, settings)


def _verify_ws_auth(websocket: WebSocket) -> bool:
    """Verify WebSocket authorization against JWT or API token configuration."""
    settings = getattr(websocket.app.state, "settings", None) or get_settings()
    token = _extract_token(websocket.headers, websocket.query_params, websocket.cookies)
    return _is_token_authorized(token, settings)


def _error(message: str, status_code: int) -> JSONResponse:
    """Build a JSON error envelope without leaking server internals."""
    return JSONResponse({"detail": message}, status_code=status_code)


def _normalize_audio_to_wav(input_path: Path, output_path: Path) -> bool:
    """Normalize input audio (WAV, WebM, etc.) to 16kHz mono PCM WAV via bundled imageio_ffmpeg."""
    try:
        import imageio_ffmpeg

        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        cmd = [
            ffmpeg_exe,
            "-y",
            "-i",
            str(input_path),
            "-ar",
            "16000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]
        res = subprocess.run(cmd, capture_output=True, timeout=15)  # noqa: S603
        return res.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0
    except Exception as exc:
        logger.warning(f"Audio ffmpeg conversion failed: {exc}")
        return False


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
    """Select the highlighted mask for a timeline state based on active workflow step."""
    if "modal" in state_label:
        return 4

    # Extract step number from state_label (e.g. "step_1", "step_2", "step_3_final")
    step_match = re.search(r"step_(\d+)", state_label)
    if step_match:
        step_num = int(step_match.group(1))
        if trace is not None:
            for rec in trace.records:
                if rec.step.step_id == step_num:
                    return rec.step.target_mask_id
            for st in trace.plan.steps:
                if st.step_id == step_num:
                    return st.target_mask_id
        return step_num

    if "final" in state_label:
        if trace is not None and trace.records:
            return trace.records[-1].step.target_mask_id
        return 4

    # Initial state -> Step 1 target
    if trace is not None and trace.plan.steps:
        return trace.plan.steps[0].target_mask_id
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
                "GET /api/frames/live",
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
    settings = getattr(_request.app.state, "settings", None) or get_settings()
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
    if not _verify_auth(request):
        return _error("Unauthorized: valid API token required.", 401)
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
    if not _verify_auth(request):
        return _error("Unauthorized: valid API token required.", 401)

    settings = getattr(request.app.state, "settings", None) or get_settings()
    max_bytes = settings.max_upload_bytes

    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > max_bytes:
                max_mb = max_bytes // (1024 * 1024)
                return _error(f"Payload exceeds maximum allowed size of {max_mb}MB.", 413)
        except ValueError:
            return _error("Invalid Content-Length header.", 400)

    try:
        form = await request.form()
    except Exception:
        return _error("Request body must be multipart form data.", 400)
    upload = form.get("audio")
    workflow_id = form.get("workflow_id", "w2")
    if not isinstance(upload, UploadFile) or not upload.filename:
        return _error("Multipart field 'audio' with a WAV file is required.", 400)
    filename_lower = upload.filename.lower()
    if not (filename_lower.endswith(".wav") or filename_lower.endswith(".webm")):
        return _error("Voice transcribe requires a WAV file.", 400)
    if workflow_id not in ("w1", "w2"):
        return _error("Unknown workflow_id; expected 'w1' or 'w2'.", 400)
    try:
        with tempfile.TemporaryDirectory(prefix="musepilot_voice_") as tmpdir:
            input_ext = ".webm" if filename_lower.endswith(".webm") else ".wav"
            input_path = Path(tmpdir) / f"input{input_ext}"
            total_bytes = 0
            with input_path.open("wb") as f:
                while chunk := await upload.read(1024 * 1024):
                    total_bytes += len(chunk)
                    if total_bytes > max_bytes:
                        max_mb = max_bytes // (1024 * 1024)
                        return _error(
                            f"Audio file exceeds maximum allowed size of {max_mb}MB.",
                            413,
                        )
                    f.write(chunk)
            if total_bytes == 0:
                return _error("Uploaded audio file is empty.", 400)

            # Normalize to 16kHz mono PCM WAV for Meta Voice Transcribe API
            audio_path = Path(tmpdir) / "command.wav"
            if input_ext == ".webm":
                if not _normalize_audio_to_wav(input_path, audio_path):
                    return _error("Could not decode audio format.", 400)
            else:
                if not _normalize_audio_to_wav(input_path, audio_path):
                    audio_path = input_path

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
    raw_id = request.path_params.get("trace_id", "")
    if not _TRACE_ID_RE.match(raw_id):
        return _error("Invalid trace_id; must be alphanumeric with hyphens or underscores.", 400)
    trace = TraceStore().find_trace(raw_id)
    if trace is None:
        return _error("Trace not found.", 404)
    return JSONResponse(trace.model_dump(mode="json"))


async def get_states(request: Request) -> JSONResponse:
    """Return the visual-state timeline labels for a workflow and trace."""
    params = request.query_params
    workflow_id = params.get("workflow", "w1").lower()
    if workflow_id not in ("w1", "w2"):
        return _error("Unknown workflow; expected 'w1' or 'w2'.", 400)
    trace_id = params.get("trace_id")
    if trace_id and not _TRACE_ID_RE.match(trace_id):
        return _error("Invalid trace_id query parameter.", 400)
    trace = _resolve_trace(trace_id, workflow_id)
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
    trace_id = params.get("trace_id")
    if trace_id and not _TRACE_ID_RE.match(trace_id):
        return _error("Invalid trace_id parameter.", 400)
    return workflow_id, state_label, trace_id


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
    settings = getattr(request.app.state, "settings", None) or get_settings()
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


class LiveMirrorManager:
    """High-framerate in-memory double-buffered streamer for live device mirrors."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[bytes, str, float, int]] = {}
        self._lock = threading.Lock()
        self._active_until: dict[str, float] = {}
        self._workers: dict[str, list[threading.Thread]] = {}
        self._seq: dict[str, int] = {}

    def get_frame(
        self,
        driver_name: str,
        serial: str | None = None,
        img_format: str = "png",
        max_age: float = 0.08,
    ) -> tuple[bytes, str]:
        data, media_type, _seq = self.get_frame_with_seq(
            driver_name=driver_name,
            serial=serial,
            img_format=img_format,
            max_age=max_age,
        )
        return data, media_type

    def get_frame_with_seq(
        self,
        driver_name: str,
        serial: str | None = None,
        img_format: str = "png",
        max_age: float = 0.08,
    ) -> tuple[bytes, str, int]:
        key = f"{driver_name}:{serial or ''}:{img_format}"
        now = time.time()
        self._active_until[key] = now + 20.0

        if driver_name in ("adb", "desktop"):
            self._ensure_worker(key, driver_name, serial, img_format)

        with self._lock:
            cached = self._cache.get(key)
            if cached is not None:
                if driver_name in ("adb", "desktop") or (now - cached[2]) < max_age:
                    return cached[0], cached[1], cached[3]

        return self._capture_and_store(key, driver_name, serial, img_format)

    def _ensure_worker(
        self, key: str, driver_name: str, serial: str | None, img_format: str
    ) -> None:
        with self._lock:
            existing = [t for t in self._workers.get(key, []) if t.is_alive()]
            target_workers = 2 if driver_name == "adb" else 1
            if len(existing) >= target_workers:
                self._workers[key] = existing
                return

            needed = target_workers - len(existing)
            for idx in range(needed):
                stagger_s = 0.16 * idx

                def loop(delay: float = stagger_s) -> None:
                    if delay > 0:
                        time.sleep(delay)
                    try:
                        driver = get_device_driver(driver_name, serial=serial)
                    except Exception as exc:
                        logger.debug(f"Live mirror worker driver init failed: {exc}")
                        return
                    sleep_interval = 0.015 if driver_name == "adb" else 0.04
                    while time.time() < self._active_until.get(key, 0):
                        try:
                            self._capture_and_store(
                                key, driver_name, serial, img_format, driver=driver
                            )
                        except Exception as exc:
                            logger.debug(f"Live mirror background capture: {exc}")
                            time.sleep(0.15)
                        time.sleep(sleep_interval)

                t = threading.Thread(
                    target=loop, daemon=True, name=f"live-mirror-{key}-{len(existing) + idx}"
                )
                existing.append(t)
                t.start()
            self._workers[key] = existing

    def _capture_and_store(
        self,
        key: str,
        driver_name: str,
        serial: str | None,
        img_format: str,
        driver: Any | None = None,
    ) -> tuple[bytes, str, int]:
        if driver is None:
            driver = get_device_driver(driver_name, serial=serial)
        if driver is not None:
            if img_format == "jpeg" and hasattr(driver, "capture_preview_image"):
                image = driver.capture_preview_image(max_width=540)
            else:
                frame = driver.capture_frame("live_preview")
                image = frame.image
        else:
            capture = ScreenCaptureEngine()
            frame = capture.render_canvas_state("w1", "initial")
            image = frame.image

        buffer = io.BytesIO()
        if img_format == "jpeg":
            if image.mode != "RGB":
                image = image.convert("RGB")
            if image.width > 540:
                h = int(image.height * (540 / image.width))
                image = image.resize((540, h), Image.Resampling.BILINEAR)
            image.save(buffer, format="JPEG", quality=75, optimize=False)
            media_type = "image/jpeg"
        else:
            image.save(buffer, format="PNG")
            media_type = "image/png"

        data = buffer.getvalue()
        now = time.time()
        with self._lock:
            seq = self._seq.get(key, 0) + 1
            self._seq[key] = seq
            self._cache[key] = (data, media_type, now, seq)
        return data, media_type, seq


GLOBAL_LIVE_MIRROR = LiveMirrorManager()


async def get_live_frame(request: Request) -> Response | JSONResponse:
    """Capture and return the current live screen frame from the target device as PNG or JPEG."""
    driver_name = request.query_params.get("driver", "simulated").lower()
    serial = request.query_params.get("serial")
    img_format = request.query_params.get("format", "png").lower()
    if driver_name not in ("simulated", "desktop", "adb"):
        return _error("Unknown driver; expected 'simulated', 'desktop', or 'adb'.", 400)
    if img_format not in ("png", "jpeg", "jpg"):
        return _error("Unknown format; expected 'png' or 'jpeg'.", 400)
    normalized_format = "jpeg" if img_format in ("jpeg", "jpg") else "png"
    try:
        data, media_type, seq = await run_in_threadpool(
            GLOBAL_LIVE_MIRROR.get_frame_with_seq,
            driver_name,
            serial,
            normalized_format,
        )
        return Response(
            data,
            media_type=media_type,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Frame-Seq": str(seq),
                "Access-Control-Expose-Headers": "X-Frame-Seq",
            },
        )
    except Exception as exc:
        logger.warning(f"Live frame capture failed: {exc}")
        return _error(f"Live capture failed: {exc}", 502)


async def get_benchmark(_request: Request) -> JSONResponse:
    """Evaluate historical traces and return the benchmark report."""
    report = await run_in_threadpool(BenchmarkEngine().evaluate_traces)
    return JSONResponse(json.loads(report.to_json()))


async def stream_run_spans(websocket: WebSocket) -> None:
    """Stream live telemetry spans for a run, then send the final trace."""
    settings = getattr(websocket.app.state, "settings", None) or get_settings()

    # Rate limiting on WebSocket connections
    if getattr(settings, "rate_limit_enabled", True):
        client_ip = websocket.client.host if websocket.client else "127.0.0.1"
        limit = getattr(settings, "rate_limit_mutation_per_minute", 30)
        allowed, _, retry_after = GLOBAL_RATE_LIMITER.check(f"{client_ip}:mutation", limit=limit)
        if not allowed:
            await websocket.accept()
            await websocket.send_json(
                {
                    "type": "error",
                    "detail": f"Rate limit exceeded ({limit} requests/minute). Please slow down.",
                    "retry_after": retry_after,
                }
            )
            await websocket.close(code=4429)
            return

    if not _verify_ws_auth(websocket):
        await websocket.accept()
        await websocket.send_json(
            {"type": "error", "detail": "Unauthorized: valid JWT or API token required."}
        )
        await websocket.close(code=4401)
        return
    await websocket.accept()
    try:
        payload = await websocket.receive_json()
    except WebSocketDisconnect:
        return
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
        last_frame_seq: int = GLOBAL_FRAME_BUFFER.seq
        sent_record_count: int = 0
        sent_event_count: int = 0
        loop = asyncio.get_running_loop()
        future = loop.run_in_executor(None, _execute_run_blocking, run_request)
        try:
            while not future.done():
                await _drain_spans(websocket, sent_span_ids)
                if GLOBAL_FRAME_BUFFER.seq > last_frame_seq:
                    last_frame_seq = GLOBAL_FRAME_BUFFER.seq
                    if GLOBAL_FRAME_BUFFER.latest_event is not None:
                        await websocket.send_json(GLOBAL_FRAME_BUFFER.latest_event)
                while sent_event_count < len(GLOBAL_RECORD_BUFFER.events):
                    evt = GLOBAL_RECORD_BUFFER.events[sent_event_count]
                    sent_event_count += 1
                    await websocket.send_json(evt)
                while sent_record_count < len(GLOBAL_RECORD_BUFFER.records):
                    rec = GLOBAL_RECORD_BUFFER.records[sent_record_count]
                    sent_record_count += 1
                    await websocket.send_json({"type": "step_record", "record": rec})
                await asyncio.sleep(0.05)
            await _drain_spans(websocket, sent_span_ids)
            if (
                GLOBAL_FRAME_BUFFER.seq > last_frame_seq
                and GLOBAL_FRAME_BUFFER.latest_event is not None
            ):
                await websocket.send_json(GLOBAL_FRAME_BUFFER.latest_event)
            while sent_event_count < len(GLOBAL_RECORD_BUFFER.events):
                evt = GLOBAL_RECORD_BUFFER.events[sent_event_count]
                sent_event_count += 1
                await websocket.send_json(evt)
            while sent_record_count < len(GLOBAL_RECORD_BUFFER.records):
                rec = GLOBAL_RECORD_BUFFER.records[sent_record_count]
                sent_record_count += 1
                await websocket.send_json({"type": "step_record", "record": rec})
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


async def get_auth_token(request: Request) -> JSONResponse:
    """Return an active session JWT for frontend auto-handshake."""
    from musepilot.security import generate_jwt

    settings = getattr(request.app.state, "settings", None) or get_settings()
    jwt_sec = getattr(settings, "jwt_secret", "")
    jwt_tok = getattr(settings, "jwt_token", "")

    token = jwt_tok
    if not token and jwt_sec:
        token = generate_jwt(
            payload={"sub": "hud-operator", "role": "operator", "iss": "musepilot"},
            secret=jwt_sec,
            expires_in_seconds=86400 * 30,
        )

    if not token:
        return JSONResponse({"token": "", "auth_required": False})

    response = JSONResponse({"token": token, "token_type": "Bearer", "auth_required": True})
    response.set_cookie("musepilot_jwt", token, path="/", samesite="lax", httponly=True)
    return response


def create_app(settings: Any | None = None) -> Starlette:
    """Build the MusePilot HUD API application."""
    active_settings = settings or get_settings()
    routes: list[Route | WebSocketRoute | Mount] = [
        Route("/api/auth/token", get_auth_token),
        Route("/api/health", get_health),
        Route("/api/health/", get_health),
        Route("/health", get_health),
        Route("/health/", get_health),
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
        Route("/api/frames/live", get_live_frame),
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
        allow_origins=active_settings.allowed_origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        allow_credentials=True,
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(JWTSessionCookieMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        limiter=GLOBAL_RATE_LIMITER,
        settings_getter=lambda: getattr(app.state, "settings", active_settings),
    )
    app.state.settings = active_settings
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
