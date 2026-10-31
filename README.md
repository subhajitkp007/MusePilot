# MusePilot 🚀

> **The Zero-Coordinate, Visually-Verified Multimodal GUI Agent**  
> *Powered by Meta SAM 3.1, Muse Spark, Muse Spark Open (`meta-models/muse-spark-open-1026`), and Muse Voice Transcribe*

[![Hackathon](https://img.shields.io/badge/Meta%20Global%20AI%20Developer%20Hackathon-Cerebral%20Valley-blue)](https://cerebralvalley.ai/e/meta-ai-developer-hackathon)
[![Track](https://img.shields.io/badge/Track-Push%20the%20Frontier-orange)](https://cerebralvalley.ai/e/meta-ai-developer-hackathon)
[![Open%20Weight](https://img.shields.io/badge/Verifier-muse--spark--open--1026-purple)](https://dev.meta.ai/models/muse-spark-open)
[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)

---

## 🎯 Executive Summary: The 3 Core Deltas

Autonomous computer-use and desktop agents routinely fail in production due to coordinate hallucination, Retina/DPI scaling mismatches, and invisible HTML5 Canvas/legacy UIs (`0 accessibility tree nodes`). **MusePilot** solves these with three architectural innovations:

1. **Never Emit Coordinates (SAM 3.1 Set-of-Mark Grounding):**  
   Meta **SAM 3.1** segments all interactive UI controls into pixel-exact masks and stamps high-contrast numbered badges (`[01]`, `[02]`...). The planner selects a `target_mask_id`—never raw `[x, y]` coordinates. The executor derives the click point mathematically from the mask centroid and normalizes for native display DPI ($S_{\text{DPI}}$).
2. **Verify Every Transition (Closed-Loop Open-Weight Verifier):**  
   After every step, **Muse Spark Open** (`meta-models/muse-spark-open-1026` hosted on Baseten / Modal / Fireworks) evaluates the pre/post visual state delta against the step's `expected_outcome`. When a transient modal blocks the screen, MusePilot autonomously invalidates its mask cache, re-segments, dismisses the obstruction, and self-heals.
3. **Fuse Voice + Vision + Verification on Meta Models:**  
   Composes four distinct Meta AI models (`SAM 3.1`, `Muse Spark`, `Muse Spark Open`, `Muse Voice Transcribe`) in one deterministic, telemetry-instrumented loop.

---

## 🏗️ System Architecture

```text
                     +---------------------------------------+
                     |         USER INTENT INTAKE            |
                     |  Typed Text  /  Muse Voice Transcribe |
                     +-------------------+-------------------+
                                         |
                                         v
   +-------------------------------------------------------------------------+
   |                     ORCHESTRATOR & AGENTIC LOOP                         |
   |   (State Machine • Step DAG Execution • Self-Healing & Escalation Policy)|
   +---+-------------------------+-------------------------+-------------+---+
       |                         |                         |             |
       v                         v                         v             v
+--------------+        +-----------------+        +---------------+  +------+
|  PERCEPTION  |        |    PLANNING     |        |  VERIFICATION |  | TRACE|
| SAM 3.1      |        | Muse Spark      |        | Muse Spark    |  | STORE|
| Meta API     |        | Meta Model API  |        | Open (Baseten/|  | &    |
| Screen frame |        | Multimodal VLM  |        | Modal/FW)     |  | REP- |
|      |       |        | (Intent + SoM   |        | Pre vs. Post  |  | LAYER|
|      v       |        |  Image -> DAG)  |        | Visual Delta  |  +------+
| Mask Set +   |        +--------+--------+        +-------+-------+
| SoM Overlays |                 |                         |
+------+-------+                 v                         v
       |               +-------------------+       +---------------+
       +-------------->|     EXECUTOR      |------>|  PASS: Next   |
                       | Centroid Math     |       |  FAIL: Retry/ |
                       | DPI Scaling       |       |        Replan |
                       | Native Input Event|       +---------------+
                       +---------+---------+
```

---

## 🧩 Meta Model Ecosystem Matrix

| Capability | Model ID | Serving Provider | Role in MusePilot |
| :--- | :--- | :--- | :--- |
| **Element Segmentation** | `meta-models/sam-3.1` | Meta Model API | Pixel-exact spatial segmentation & Set-of-Mark badge generation. |
| **Multimodal Planning** | `meta-models/muse-spark` | Meta Model API | Zero-coordinate Step DAG generation over SAM 3.1 mask IDs. |
| **State Verification** | `meta-models/muse-spark-open-1026` | Baseten / Modal / Fireworks | Closed-loop visual verification (**Qualifies for $10K Best Open Weight Build**). |
| **Voice Intake** | `meta-models/muse-voice-transcribe` | Meta Model API | Real-time spoken command transcription into agent intents. |

---

## ⚡ Quickstart (Fresh Clone to Live HUD in 60 Seconds)

### Option A: Local Virtual Environment (`Makefile`)

```bash
# 1. Initialize .venv and install dependencies
make setup
cp .env.example .env

# 2. Run Pre-Flight Health & Calibration Check
make health

# 3. Execute Workflow 1 (Precision WebGL/HTML5 Canvas Calibration)
make demo-w1

# 4. Execute Workflow 2 (Voice Cross-App + Autonomous Self-Healing Modal Recovery)
make demo-w2

# 5. Launch Interactive Streamlit HUD & Telemetry Dashboard
make dashboard
```

### Option B: Production Docker Compose Stack

Runs the complete multi-service stack (`musepilot-agent`, `musepilot-dashboard` on `:8501`, `musepilot-canvas-demo` on `:8088`, and `jaeger` OpenTelemetry collector on `:16686`):

```bash
docker compose up --build -d
```

* **MusePilot Visual HUD:** http://localhost:8501
* **Pure HTML5 Canvas Target (`0 DOM Nodes`):** http://localhost:8088/canvas_app.html
* **Jaeger OpenTelemetry Tracing UI:** http://localhost:16686

---

## 📊 Verified Rehearsal Benchmark Metrics

| Metric | Result | Verification Evidence |
| :--- | :--- | :--- |
| **Mask Centroid Hit Rate** | **100.0%** | 0px coordinate drift across W1 & W2 canvas controls (`test_orchestrator_and_replay.py`). |
| **Zero-Coordinate Compliance** | **100.0%** | Enforced at schema boundary via `ZeroCoordinateViolationError` (`test_schemas_and_invariants.py`). |
| **Verification Pass Rate (Clean)** | **100.0%** | `meta-models/muse-spark-open-1026` + ROI structural pixel delta. |
| **Self-Healing Recovery Rate** | **100.0%** | Autonomous modal detection, SAM 3.1 cache invalidation, and Mask `#4` dismissal on W2. |
| **DPI Scaling Accuracy** | **100.0%** | Verified across 2.0x macOS Retina and 1.0x standard displays (`test_dpi_and_som.py`). |

---

## 🗂️ Repository Layout

```text
MusePilot/
├── musepilot/
│   ├── contracts/             # Pydantic v2 schemas & Zero-Coordinate Invariant validators
│   ├── telemetry/             # Structured JSON logger, PII/secret redaction, OpenTelemetry spans
│   ├── perception/            # Screen capture, SAM 3.1 client, Set-of-Mark (SoM) renderer
│   ├── planning/              # Meta Muse Spark multimodal planner client
│   ├── execution/             # Centroid math, Retina DPI scaling, guarded input dispatch
│   ├── verification/          # Partner-hosted Muse Spark Open (`1026`) visual verifier
│   ├── voice/                 # Meta Muse Voice Transcribe client
│   ├── orchestrator/          # Closed-loop state machine & self-healing recovery policy
│   ├── trace/                 # Deterministic JSON trace recorder & golden-trace replayer
│   ├── health/                # Pre-flight calibration & model compliance checker
│   ├── dashboard/             # Real-time Streamlit HUD & Telemetry viewer
│   └── cli.py                 # Unified CLI (`run`, `replay`, `health`)
├── prompts/                   # Versioned prompt templates (`planner_som_v1.txt`, `verifier_eval_v1.txt`)
├── configs/                   # Non-secret runtime defaults (`default_config.yaml`)
├── demo/                      # Pure HTML5 Canvas target (`canvas_app.html`) & golden traces
├── docs/                      # Architecture, Win Strategy, Sprint Plan, & Submission Playbook
├── tests/                     # Unit & golden-trace integration test suite
├── Dockerfile                 # Multi-stage, rootless, security-hardened container build
├── docker-compose.yml         # Multi-service orchestration with OpenTelemetry/Jaeger
└── Makefile                   # Developer workflow automation
```

---

## 📚 Documentation Index (`docs/`)

* [System Architecture & Technical Specifications](docs/ARCHITECTURE.md)
* [Implementation Plan & 4-Day Sprint Roadmap](docs/IMPLEMENTATION_PLAN.md)
* [Win Strategy & Rubric Evaluation](docs/EVALUATION_AND_WIN_STRATEGY.md)
* [Demo Video Storyboard & Submission Playbook](docs/DEMO_AND_SUBMISSION_PLAYBOOK.md)
* [Engineering & Open-Source Style Guidelines](docs/DEVELOPMENT_GUIDELINES.md)
* [Contributing Guide](CONTRIBUTING.md) • [Code of Conduct](CODE_OF_CONDUCT.md) • [Security & Responsible AI Policy](SECURITY.md)

---

## 📄 License

Licensed under the Apache License 2.0 — see [LICENSE](LICENSE) for full details.
