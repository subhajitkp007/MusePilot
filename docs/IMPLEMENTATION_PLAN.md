# MusePilot — Implementation Plan & Sprint Roadmap

> **Timeline:** 4-Day Execution Sprint: Oct 31 → Nov 4, 2026  
> **Submission Deadline:** November 4 at 9:00 PM ET (Self-imposed freeze & submit buffer: Nov 4 by 6:00 PM ET).  
> **Core Objective:** Build a bulletproof, visually magnetic MVP with 2 frozen workflows, 4 integrated Meta models, and zero demo-day flakiness.

---

## 1. Concrete Workflow Definitions (Frozen Scope)

To eliminate scope creep and ensure 100% reliability, the hackathon MVP targets two specific high-impact workflows:

### Workflow 1 (W1) — Precision Canvas Control (The Frontier Grounding Story)
* **Target Environment:** An HTML5 Canvas / WebGL interactive engineering dashboard (where browser DOM inspector shows only a single `<canvas>` element and zero accessibility nodes).
* **The Task:** "Calibrate the simulation parameters: set the frequency slider to 75%, toggle the adaptive damping switch, and trigger the benchmark run."
* **What It Proves:**
  - Standard DOM/accessibility-based automation tools fail completely.
  - SAM 3.1 segments the canvas sliders, switches, and buttons into pixel-exact masks.
  - Muse Spark selects the correct mask IDs without guessing coordinates.
  - Centroid-based drag & click execution operates seamlessly inside the canvas.
  - Muse Spark Open visually verifies that the simulation waveform updated.

### Workflow 2 (W2) — Voice-Driven Cross-App Automation (The Agentic Agency Story)
* **Target Environment:** Cross-application desktop workflow (e.g., Browser Dashboard to Desktop Portal).
* **The Task:** Voice command via Muse Voice Transcribe: *"Extract today's system anomaly metrics from the monitoring console and file an urgent incident dispatch report."*
* **What It Proves:**
  - Real-time voice intent capture and execution.
  - Autonomous multi-step planning across window boundaries.
  - Robust state verification at every transition.
  - Self-healing demonstration: When a transient confirmation dialog appears, MusePilot detects the block, replans, dismisses the modal, and resumes execution.

---

## 2. Milestone Breakdown (Musts vs. Shoulds)

```
+---------------------------------------------------------------------------------------+
| CORE HACKATHON DELIVERABLES (MUST-HAVES)                                              |
| M1: SAM 3.1 Frame Capture & Set-of-Mark Overlay Generation                            |
| M2: DPI-Invariant Centroid Calculation & OS Input Execution Engine                    |
| M3: Muse Spark Multimodal Planner with Structured Mask-ID DAG Output                  |
| M4: Closed-Loop Visual Verifier via Muse Spark Open (Baseten/Modal/Fireworks)         |
| M5: Hands-Free Voice Intake via Muse Voice Transcribe                                 |
| M6: Real-Time HUD Overlay (Neon Polygons, Mask ID Chips, Green Verification Ticks)    |
| M7: Deterministic JSON Trace Recorder & Replay Fallback Engine                        |
| M8: Inference Partner Open-Weight Endpoint Documentation & Proof                      |
| M9: Quantitative Metrics Dashboard (Grounding accuracy, Verification precision)       |
+---------------------------------------------------------------------------------------+
| HIGH-VALUE EXTENSIONS (SHOULD-HAVES)                                                  |
| S1: Injected Failure & Live Self-Healing Demo Moment (proves true agentic behavior)   |
| S2: Pre-flight One-Click Calibration & Health-Check Tool (`musepilot.health`)         |
| S3: Live Speech Synthesis Confirmation ("Task verified and completed")                |
+---------------------------------------------------------------------------------------+
```

---

## 3. Day-by-Day Sprint Schedule

### Day 0: Oct 31 (Today) — Architectural Lock & Environment Setup
- [x] Convert and review hackathon rules and judging criteria.
- [x] Lock architecture, win strategy, demo script, and development guidelines.
- [ ] Claim $150 Meta Model API credits via official Google Form.
- [ ] Apply for $100 partner credits (Baseten, Modal, Fireworks forms).
- [ ] Initialize Python environment, configuration templates, and directory structure.

### Day 1: Nov 1 — Perception & Grounded Execution (M1, M2, M7-part)
- [ ] Implement `ScreenCapture` module with multi-monitor & Retina DPI scaling detection.
- [ ] Integrate SAM 3.1 client via Meta Model API.
- [ ] Build `SetOfMarkGenerator`: filter raw masks and render crisp, high-contrast numeric ID badges.
- [ ] Implement `Executor`: compute mathematical centroids from mask polygons and dispatch native OS clicks/types.
- [ ] Build initial `TraceRecorder` to capture frames, masks, and actions into JSON traces.
- [ ] **Exit Criterion:** Able to capture the W1 canvas screen, render the Set-of-Mark overlay, and click/type into 3 distinct UI elements using their Mask IDs.

### Day 2: Nov 2 — Multimodal Planning & Open-Weight Verification (M3, M4, M8)
- [ ] Implement `Planner` using `Muse Spark` via Meta Model API:
  - Input: SoM annotated frame + user intent.
  - Output: Strictly validated JSON Step DAG with target mask IDs and `expected_outcome` assertions.
- [ ] Deploy or connect `meta-models/muse-spark-open-1026` on partner inference (Baseten / Modal / Fireworks).
- [ ] Implement `Verifier`:
  - Crop region of interest around target mask before and after action.
  - Run structural similarity (SSIM) delta check.
  - Query `Muse Spark Open` for semantic state transition verification (`PASS` / `FAIL`).
- [ ] Implement Orchestrator self-healing loop: on `FAIL`, retry once with hint, then replan.
- [ ] **Exit Criterion:** W1 executes end-to-end autonomously from typed prompt with closed-loop verification gating each step. **Feature Freeze for W1.**

### Day 3: Nov 3 — Voice Intake, HUD Dashboard, & Rehearsals (M5, M6, M9, S1, S2)
- [ ] Implement `VoiceIntake` using Meta `Muse Voice Transcribe` client.
- [ ] Build cross-platform Flutter HUD + Starlette API server displaying:
  - Live marked screen feed with glowing target indicator.
  - Step DAG progress bar and active task card.
  - Real-time green verification checkmarks and latency meters.
- [ ] Build `musepilot.health` CLI check (validates API keys, endpoints, display DPI, target app bounds).
- [ ] Run 10 full rehearsal trials on W1 and W2. Log grounding accuracy and verification precision for the metrics card.
- [ ] Inject intentional modal pop-up during W2 rehearsal to verify and record the self-healing recovery moment.
- [ ] **Exit Criterion:** 3 consecutive clean, uninterrupted live runs achieved for both W1 and W2.

### Day 4: Nov 4 — Video Production, Code Audit, & Submission (Buffer: Submit by 6 PM ET)
- [ ] Record the 3-minute demo video following the exact storyboard in `DEMO_AND_SUBMISSION_PLAYBOOK.md`.
- [ ] Edit video: add voiceover, captions, callout cards for model roles, and the miss-vs-lock comparison hook.
- [ ] Upload video to YouTube / Loom (ensure public / unlisted link is accessible from incognito).
- [ ] Code audit: verify all API keys are removed, Apache-2.0 license headers included, README is clean and reproducible.
- [ ] File official submission on Cerebral Valley platform before **6:00 PM ET** (3 hours before 9:00 PM ET deadline).
- [ ] Prepare social media launch thread for the **$20K Most Viral Project** prize.

---

## 4. Quantitative Metrics to Report in README & Demo Video

To prove engineering rigor and technical depth to judges, the submission will present verified benchmark metrics collected across rehearsal runs:

| Metric | Target | Description |
| :--- | :--- | :--- |
| **Mask Centroid Hit Rate** | **100%** | Target element clicked within mask boundaries (0 coordinate drift). |
| **Verification Precision** | **$\ge 95\%$** | Accuracy of `Muse Spark Open` verdicts compared against human ground-truth labels. |
| **Self-Healing Recovery Rate** | **$100\%$** | Successful recovery and resumption after unexpected dialog obstruction. |
| **DPI Translation Accuracy** | **$100\%$** | Zero misclicks across high-DPI (2.0x Retina) and standard (1.0x) displays. |
| **Replay Determinism** | **$100\%$** | Full fidelity trace playback without model calls. |
