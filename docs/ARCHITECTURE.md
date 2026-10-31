# MusePilot — System Architecture & Technical Specifications

> **Zero-Shot Multimodal GUI Agent**  
> Pixel-Exact SAM 3.1 Set-of-Mark Grounding • Muse Spark Multimodal Planning • Closed-Loop Open-Weight Visual Verification • Muse Voice Transcribe  
> *Target Track:* Push the Frontier (Indie Developer) • *Bonus Alignment:* Best Agentic + Best Open Weight + Most Viral

---

## 1. System Overview & Core Novelty

Current computer-use agents (like raw OS-world agents or standard VLMs) attempt to predict `[x, y]` coordinates directly from screen images. This approach fails because:
* A tiny shift in window position or display scaling (e.g., macOS Retina 2x vs 1x) causes the model to click dead space.
* HTML5 Canvas, WebGL, custom desktop portals, and legacy applications lack accessible DOM or accessibility tree elements.
* Open-loop execution cascades into silent failures when network latency, dialog boxes, or modals appear.

**MusePilot** introduces a **zero-coordinate, visually-verified perception-action architecture**:
1. **Perception:** SAM 3.1 segments every interactive UI element and composites a **Set-of-Mark (SoM)** numbered badge overlay onto the frame.
2. **Planning:** Muse Spark analyzes the marked frame and selects **Mask IDs** (e.g. `[Mask #14]`), generating a verifiable DAG.
3. **Execution:** The execution engine calculates the mathematical centroid of the segmented mask and scales it to the native display DPI.
4. **Closed-Loop Verification:** Muse Spark Open (`meta-models/muse-spark-open-1026` via partner inference) compares pre-action and post-action visual states to deterministically verify state transitions.

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
                                 |
                                 v
                       +-------------------+
                       | REAL-TIME HUD /   |
                       | STREAMLIT DASHBRD |
                       | Neon Masks, Plan, |
                       | Verification Check|
                       +-------------------+
```

---

## 2. Component Specifications & Contracts

### A. Perception Engine: SAM 3.1 & Set-of-Mark (SoM) Generator
* **Input:** Raw OS frame buffer capture ($W \times H$, RGB).
* **Model:** Meta SAM 3.1 (Segment Anything Model 3.1 via Meta Model API).
* **Processing Pipeline:**
  1. **Step-Boundary Capture:** Captures screen on stable step boundaries; skips redundant capture during active animation.
  2. **Mask Generation:** Runs SAM 3.1 segmentation over the active app window or full screen.
  3. **Heuristic Filter & Clustering:** Suppresses background clutter (e.g., massive background masks $>80\%$ area or micro-artifacts $<10\text{px}^2$).
  4. **Set-of-Mark Compositing:** Renders high-contrast, semi-transparent neon bounding polygons and bright numbered badge pills (`[01]`, `[02]`, `[03]`...) at each mask centroid.
  5. **Screen Hash Caching:** If the UI has not changed, re-uses the cached mask set (zero-latency perception on stable screens).
* **Output:**
  - `SoM Annotated Image` (passed to Muse Spark Planner).
  - Mask Metadata Registry: `{mask_id: int, bbox: [x1, y1, x2, y2], centroid: [cx, cy], area: int, polygon: list}`.

### B. Planner: Muse Spark (Meta Model API)
* **Input:** User intent + current task history + active `SoM Annotated Image`.
* **Model:** `Muse Spark` multimodal reasoning model via Meta Model API.
* **Output Contract:** Strictly schema-validated JSON Step DAG. Raw coordinates are forbidden by prompt schema and validation interceptors:
  ```json
  {
    "plan_summary": "Fill shipping form and submit",
    "current_step": {
      "step_id": 1,
      "operation": "click",
      "target_mask_id": 14,
      "input_value": null,
      "expected_outcome": "The input field at Mask 14 shows a focused cursor and blue highlight border",
      "reasoning": "Mask 14 corresponds to the 'Customer Name' input field on the canvas form."
    },
    "remaining_steps": [
      {"step_id": 2, "operation": "type", "target_mask_id": 14, "input_value": "Jane Doe", "expected_outcome": "Text 'Jane Doe' visible inside field"},
      {"step_id": 3, "operation": "click", "target_mask_id": 22, "input_value": null, "expected_outcome": "Submission success dialog appears with 'Order Confirmed'"}
    ]
  }
  ```

### C. Execution Engine: DPI-Invariant Native Controller
* **Input:** Step definition containing `target_mask_id` + Mask Metadata.
* **Math & Coordinate Resolution:**
  - Mask centroid calculated in frame space:
    $$\bar{x} = \frac{1}{N} \sum_{i=1}^N x_i, \quad \bar{y} = \frac{1}{N} \sum_{i=1}^N y_i$$
  - Display Scaling Normalization: Translates backing-store pixel coordinates to OS virtual points:
    $$x_{\text{OS}} = \frac{\bar{x}}{S_{\text{DPI}}}, \quad y_{\text{OS}} = \frac{\bar{y}}{S_{\text{DPI}}}$$
    *(Crucial for macOS Retina 2.0x scaling and Windows 125%/150% fractional scaling).*
* **Input Dispatch:** Native OS events (macOS Quartz/CGEvent, or cross-platform `pyautogui` / `pynput`).
* **Output:** Pre-action frame, Post-action frame, execution timestamp, and receipt.

### D. Verifier: Muse Spark Open (Partner-Hosted Open Weight Model)
* **Input:** Pre-action frame (or crop), Post-action frame (or crop), Action executed, `expected_outcome` assertion string.
* **Model:** `meta-models/muse-spark-open-1026` hosted on Baseten, Modal, or Fireworks.
* **Dual-Tier Verification:**
  1. **Visual Delta Detector:** Calculates structural similarity (SSIM) and pixel diff mask around the target bounding box to confirm a visual state transition took place.
  2. **Semantic State Judge:** `Muse Spark Open` evaluates whether the post-state semantically matches `expected_outcome`.
* **Output Contract:**
  ```json
  {
    "verdict": "PASS",
    "confidence": 0.96,
    "observed_change": "Blue focus border appeared and cursor is active in field",
    "retry_hint": null
  }
  ```
  *(If `FAIL`: returns explicit diagnosed failure e.g., `"Dropdown did not open; clicked during loading animation"` and `retry_hint: "Wait 500ms and re-click mask"`).*

### E. Voice Intake: Muse Voice Transcribe
* **Input:** Microphone audio stream (WAV/PCM).
* **Model:** Meta `Muse Voice Transcribe` via Meta Model API.
* **Output:** Precise transcript string with confidence score, triggering automatic intent parsing into the Orchestrator.

### F. Orchestrator: Self-Healing State Machine
* **Policy:**
  - **Pass:** Advance DAG to next step; trigger green UI checkmark.
  - **Fail (Attempt 1):** Execute localized micro-retry using `retry_hint` (e.g. slight delay, re-trigger click).
  - **Fail (Attempt 2):** Invalidate mask cache, capture fresh frame, re-run SAM 3.1 SoM, and request Muse Spark to replan from current state (self-healing from unexpected modals or page changes).
  - **Fail (Attempt 3):** Graceful human-in-the-loop escalation. Highlights ambiguous area on HUD for operator override.

---

## 3. Meta Model Utilization Matrix

| Capability | Model | Serving Provider | Hackathon Judging Significance |
| :--- | :--- | :--- | :--- |
| **Element Segmentation** | SAM 3.1 | Meta Model API | Core technical novelty: eliminates coordinate hallucination on canvas/un-inspectable UIs. |
| **Agentic Planning & Reasoning** | Muse Spark (Multimodal) | Meta Model API | Interprets Set-of-Mark visual scenes; outputs structured DAGs without coordinate guessing. |
| **Closed-Loop Verification** | Muse Spark Open (`meta-models/muse-spark-open-1026`) | Baseten / Modal / Fireworks | Verifies state transitions; **Qualifies for $10K Best Open Weight Build** (verified by inference partner). |
| **Voice Command Intake** | Muse Voice Transcribe | Meta Model API | Enables live hands-free control moment in demo video. |
| **Rapid Code Acceleration** | Muse Code | Meta Developer Platform | Used to author, accelerate, and refine hackathon pipeline code. |

---

## 4. Reliability & Fail-Safe Demo Architecture

To guarantee a 100% deterministic, stutter-free 3-minute video and live judging presentation:
1. **Determinism via Trace Replayer:**
   - Every live run automatically serializes a complete JSON trace containing: screen hashes, SAM 3.1 masks, SoM annotated frames, planner prompts & outputs, actions, and verification verdicts.
   - The system features a native `--replay <trace_id>` flag. If API latency spikes or wifi drops during rehearsal or live Q&A, the replayer reproduces the exact run with full HUD overlays at full speed.
2. **Pre-Flight Health Check:**
   - A single CLI command `python -m musepilot.health` validates:
     - Meta Model API credentials and credit balance.
     - Partner inference endpoint reachability (Baseten/Modal/Fireworks).
     - Display resolution and Retina scaling factor ($S_{\text{DPI}}$).
     - Target application window positioning and bounds.
3. **Guardrails & Safe Execution:**
   - Pre-configured Action Allowlist prevents out-of-bounds clicks or accidental browser tab switches.
   - Sensitive inputs (passwords, tokens) are automatically redacted in traces, logs, and video overlays.

---

## 5. Repository Structure

```text
MusePilot/
├── musepilot/
│   ├── orchestrator/          # State machine, DAG runner, self-healing loop
│   ├── perception/            # SAM 3.1 client, mask filtering, SoM visual badge compositing, cache
│   ├── planning/              # Muse Spark multimodal client, prompt templates, DAG schemas
│   ├── execution/             # Centroid math, DPI scaling, native OS input drivers, capture
│   ├── verification/          # Visual diff engine, Muse Spark Open partner client, assertions
│   ├── voice/                 # Muse Voice Transcribe integration, live audio recorder
│   ├── dashboard/             # Real-time visual HUD (neon overlays, DAG progress, verification ticks)
│   ├── trace/                 # JSON trace recorder, golden dataset serializer, deterministic replayer
│   └── health/                # Pre-flight environment, API, and display calibration check
├── prompts/                   # Versioned, reproducible prompt files for Spark & Spark Open
│   ├── planner_som_v1.txt
│   └── verifier_eval_v1.txt
├── tests/                     # Deterministic fixture tests & schema validations (CI-ready)
├── demo/                      # Target workflow definitions (W1 Canvas, W2 Cross-App Voice)
├── configs/                   # Model IDs, partner endpoints, DPI settings (NO secrets)
├── docs/                      # Architectural specs & submission playbooks
├── .gitignore
├── README.md
└── requirements.txt
```
