## Summary
<!-- Provide a concise explanation of what this diff changes and why. -->

## Test Plan
<!-- Meta Engineering Standard: Every PR must include reproducible verification commands and output. -->
```bash
make lint
make test
make health
```
- **Recorded Trace ID (if applicable):** `trace_...`
- **Unit / Fixture Tests Added:**

## Component & Milestone Alignment
- [ ] `perception` — SAM 3.1 Segmentation & Set-of-Mark (SoM) Compositor (`M1`)
- [ ] `execution` — DPI-Invariant Centroid Math & Guarded Dispatch (`M2`)
- [ ] `planning` — Muse Spark Multimodal StepDAG Planner (`M3`)
- [ ] `verification` — Muse Spark Open (`meta-models/muse-spark-open-1026`) Closed-Loop Verifier (`M4`, `M8`)
- [ ] `voice` — Muse Voice Transcribe Intake (`M5`)
- [ ] `server` + `app/` — HUD API & Flutter Visual HUD Inspector (`M6`)
- [ ] `trace` — Deterministic Trace Store & Golden Replay Engine (`M7`)
- [ ] `orchestrator` — Self-Healing State Machine & Metrics (`M9`, `S1`)

## Architectural & Security Invariants Checklist
- [ ] **Apache-2.0 Header:** All new files include the standard `# Copyright 2026 MusePilot Authors` header.
- [ ] **Zero-Coordinate Invariant:** Planner schemas and prompts emit only `target_mask_id` (no raw `[x, y]` coordinates).
- [ ] **DPI Normalization:** Frame pixel centroids are normalized by `display_dpi_scale`.
- [ ] **Versioned Prompts:** Any prompt modifications live in `prompts/<name>_v<N>.txt` (no inline prompt strings).
- [ ] **Telemetry & Redaction:** External calls use `GLOBAL_TELEMETRY.start_span()` and pass `RedactingLogFilter` checks with zero secrets in logs or traces.
