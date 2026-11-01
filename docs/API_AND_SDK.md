# MusePilot — API & SDK Integration Guide

> Integrate zero-coordinate GUI automation into your product: run workflows
> over REST, stream live progress over WebSocket, or embed the Python SDK.

## 1. Start the server

```bash
cp .env.example .env   # add Meta + partner API keys for live mode
make server            # http://localhost:8501
```

`GET /api/openapi.json` serves the machine-readable contract. Modes:

| Mode | Behavior |
| :--- | :--- |
| `simulated` (default) | Deterministic canvas, no model calls, hermetic CI |
| `live` | Real Meta Model API calls + real device I/O; failures raise, never mock |

## 2. Python SDK quickstart

```python
from musepilot.sdk import MusePilotClient

with MusePilotClient("http://localhost:8501") as mp:
    print(mp.health())                       # readiness + model IDs
    for event in mp.run_stream("w1"):        # started -> span* -> complete
        print(event["type"])
    trace = mp.latest_trace("w1")            # full deterministic trace
    mp.som_frame("w1", "initial", trace["trace_id"])  # overlay PNG bytes
```

`MusePilotError` carries `.status_code` (`400` bad input, `502` live
model failure). Every method is covered in `tests/test_sdk.py`.

## 3. Voice-driven runs (W2 pattern)

Live W2 needs transcribed intent; the server cannot hear you, so the
client transcribes first, then runs:

```python
with MusePilotClient("http://localhost:8501") as mp:
    heard = mp.transcribe("command.wav")["transcript"]
    trace = mp.run("w2", custom_intent=heard)
```

`POST /api/voice/transcribe` accepts multipart `audio` (WAV) +
`workflow_id` and returns a `VoiceTranscript`.

## 4. WebSocket run streaming

Connect to `/ws/runs`, send a `RunRequest` (`workflow_id`,
`inject_modal`, `driver`, optional `custom_intent`), and consume:

```
{"type": "started", "workflow_id": "w1"}
{"type": "span", "span": {...}}        # per completed telemetry span
{"type": "complete", "trace": {...}}   # or {"type": "error", "detail": ...}
```

One run at a time per server; a second concurrent run gets an error.

## 5. Live-mode requirements

| Capability | Requirement |
| :--- | :--- |
| SAM 3.1 + planner + voice | `MUSEPILOT_META_API_KEY` (Meta Model API) |
| Open-weight verifier | `MUSEPILOT_PARTNER_API_KEY` (Baseten/Modal/Fireworks) |
| Real desktop/mobile input | `MUSEPILOT_ALLOW_LIVE_INPUT=true` + OS permission (macOS: System Settings > Privacy & Security > Accessibility) |

## 6. Verifier backend switch

Partner access is limited, so the live verifier backend is
configurable — no code changes needed:

```bash
# Default: open-weight verifier on partner inference
MUSEPILOT_VERIFIER_BACKEND=partner

# Meta-only: verify with muse-spark-1.3 on the Meta Model API
MUSEPILOT_VERIFIER_BACKEND=meta
```

With `meta`, verdicts carry `model_id: muse-spark-1.3` and
`partner_provider: "meta"`, so traces stay honest about which model
judged each step. When the active backend has no key, live
verification falls back to the structural ROI pixel check. Without the
input opt-in, dispatch raises `LiveInputDisabledError` instead of
touching the OS.

## 7. Flutter HUD clients

The cross-platform HUD in `app/` consumes this same API; see
[app/README.md](../app/README.md) for per-platform run instructions and
the `--dart-define=MUSEPILOT_API_BASE` override.
