# MusePilot — Engineering & Development Guidelines

> **Meta-Grade Engineering Standards for a 4-Day Hackathon Sprint**  
> High velocity • Flawless provenance • Deterministic repeatability • Zero demo vulnerabilities

---

## 1. Core Engineering Principles

1. **Impact-Driven Development:** Every single pull request / commit must directly support one of the core milestones (M1–M9) or de-risk the 3-minute demo. Speculative features are banned until after submission.
2. **Deterministic Provenance:** All commits must land with clear, descriptive messages between **October 27 and November 4, 2026**. Hackathon judges strictly verify that projects were built during the event.
3. **Zero-Coordinate Invariant:** No component may ever output, ingest, or pass raw `[x, y]` coordinates across component boundaries. The Planner outputs only `target_mask_id`. Centroids are derived mathematically by the execution engine and adjusted for DPI scaling.
4. **Verifiable Quality:** No action advances without visual evidence. Verification is not an afterthought; it is a first-class architectural gatekeeper.
5. **Radical Privacy & Security:** No secrets in code or traces. Automatic redaction of sensitive input values. Local-first execution.

---

## 2. Code Quality & Standards

* **Language & Typing:** Python 3.10+, strictly type-annotated (`typing`, `Pydantic` models for all schemas).
* **Formatting & Linting:** `ruff` or `flake8` + `black` configured once on Day 1. All code must pass cleanly.
* **Prompt Engineering Hygiene:**
  - Zero hardcoded prompt strings in Python logic.
  - Prompts must be stored in `prompts/<model>_<role>_v<N>.txt` with versioning, system instructions, and schema definitions.
* **Error Handling & Resilience:**
  - All network calls to Meta Model API or partner inference (Baseten/Modal/Fireworks) must be wrapped with:
    - Explicit timeouts (10s default).
    - Retry budgets (max 2 retries with exponential backoff).
    - Structured latency logging for benchmark reporting.
* **DPI Normalization Rule:**
  - All screen captures and mask polygons must record the active screen's physical-to-logical DPI scale factor ($S_{\text{DPI}}$). Coordinate clicks must always divide backing-store coordinates by $S_{\text{DPI}}$ to prevent offset errors on macOS Retina or Windows display scaling.

---

## 3. Testing, Fixtures, & CI Strategy

1. **Unit Tests (Fast, Offline):**
   - Step DAG schema validation.
   - Set-of-Mark badge centroid calculation and DPI normalization math.
   - Sensitive data redaction regex and filters.
   - Orchestrator self-healing state transitions.
2. **Golden Trace Fixture Tests:**
   - Pre-recorded JSON traces act as regression test fixtures.
   - The verifier is evaluated against pre-labeled golden pre/post frame pairs without incurring live API costs during testing.
3. **Pre-Flight Health Tool (`python -m musepilot.health`):**
   - Single command to run prior to recording or live Q&A.
   - Validates API tokens, model endpoints, screen dimensions, DPI scaling factor, and target app window visibility.

---

## 4. Responsible AI & Safety Guardrails

To ensure compliance with hackathon rules and present a responsible AI architecture to judges:
* **Action Allowlist:** The agent only interacts with the active target window or defined application bounding box; clicking system trays, browser settings, or external files is blocked.
* **Destructive Action Confirmation:** Operations involving deletion, external sending, or purchasing trigger an immediate operator confirmation prompt (which will be shown once in the demo video as proof of safety craft).
* **Trace Redaction:** Personal identifiable information (PII), credentials, and sensitive text fields are masked in logs, JSON traces, and visual overlays.

---

## 5. Commit & Provenance Standards

Every commit message must follow this structured format:
```text
<component>: <concise description of feature>

Evidence: <how this was tested or verified>
Milestone: <M1-M9 / S1-S3>
```

*Example:*
```text
perception: integrate SAM 3.1 client with SoM badge overlay

Evidence: 12/12 buttons segmented and labeled on canvas benchmark test
Milestone: M1
```

*Never use vague commit messages like "wip", "update", or "fixes".*
