# MusePilot — Engineering & Open-Source Style Guidelines

> **Meta Open Source Engineering Standards**  
> Atomic diffs (`Summary` + `Test Plan`) • Deterministic provenance • Strict type contracts • Zero demo vulnerabilities

---

## 1. Core Engineering Principles

1. **Focus on Impact:** Every pull request or commit must directly advance a core milestone (`M1–M9` / `S1–S3`) or strengthen reliability. Speculative complexity is deferred.
2. **Move Fast with Provenance:** Small, atomic diffs with structured commit messages and reproducible test plans inside **October 27 – November 4, 2026**.
3. **Be Open & Reproducible:** Every feature must be verifiable from a fresh clone using `make setup && make test && make health` without requiring external proprietary state.
4. **Zero-Coordinate Invariant:** No component may ever emit, ingest, or pass raw `[x, y]` coordinates across component boundaries. The Planner outputs only `target_mask_id` from Meta **SAM 3.1**; centroids are derived mathematically by the execution engine and normalized by `display_dpi_scale`.
5. **Verify, Don't Hope:** Every UI state transition is gated by `SparkOpenVerifier` (`meta-models/muse-spark-open-1026`), and every code change is gated by automated CI checks.
6. **Privacy & Security by Design:** Automatic PII and credential redaction in all logs and JSON traces (`musepilot.telemetry.redaction`).

---

## 2. Meta Open Source Code Style Conventions

### A. License Headers
Every Python, YAML, Dockerfile, and Makefile source file must begin with the standard Apache-2.0 license header:
```python
# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
```

### B. Python Typing, Docstrings, & Formatting
- **Future Annotations & Strict Typing:** Include `from __future__ import annotations` in all modules and annotate every function signature (parameters and return types).
- **Pydantic v2 Data Contracts:** All structured payloads crossing module boundaries (`MaskSet`, `StepNode`, `StepDAG`, `ActionReceipt`, `VerificationVerdict`, `RunTrace`) must live in [`musepilot/contracts/schemas.py`](../musepilot/contracts/schemas.py) with `extra="forbid"` where applicable.
- **Docstrings:** Concise, imperative one-line or Google-style docstrings on all public classes and functions explaining the contract and invariants.
- **Automated Linting & Security:** Enforced via `ruff` (`make lint` and `make format`):
  - `E`, `W` (pycodestyle), `F` (pyflakes), `I` (isort), `B` (flake8-bugbear), `UP` (pyupgrade), and `S` (flake8-bandit security scanning).

### C. Prompt Engineering & Configuration Hygiene
- **No Inline Prompts:** System prompts must never be embedded in Python code. Store all prompts in [`prompts/`](../prompts/) with explicit version tags (`prompts/planner_som_v1.txt`, `prompts/verifier_eval_v1.txt`).
- **Centralized Configuration:** All model IDs, partner endpoints, timeouts, and DPI settings are managed via [`MusePilotSettings`](../musepilot/config.py) with precedence explicit-init > `MUSEPILOT_*` env vars > `.env` file > [`configs/default_config.yaml`](../configs/default_config.yaml) > built-in defaults. Non-secret defaults live in the YAML file; secrets are env-only and must never enter the YAML.

### D. Telemetry & Logging Standards
- Never use bare `print()` statements inside library packages (`musepilot/*`, excluding CLI entry points).
- Use `get_logger(__name__)` from `musepilot.telemetry` and wrap external/model operations in `with GLOBAL_TELEMETRY.start_span("<component>.<operation>", trace_id=trace_id, model_id=...):`.

---

## 3. Diff / Pull Request Discipline (Summary + Test Plan)

Following Meta's internal engineering review culture, every commit and Pull Request must clearly document **what** changed and **how** it was verified:

### Commit Message Format
```text
<component>: <concise imperative summary>

Evidence: <exact verification result, test count, or trace ID>
Milestone: <M1-M9 / S1-S3>
```

### Pull Request Requirements
Every PR must complete [`.github/PULL_REQUEST_TEMPLATE.md`](../.github/PULL_REQUEST_TEMPLATE.md):
1. **Summary:** Architectural motivation and scope of change.
2. **Test Plan:** Exact commands executed (`make lint`, `make test`, `make health`, `make demo-w1`, `make demo-w2`) and their output.
3. **Invariant Verification:** Confirmation that the Zero-Coordinate Invariant, DPI normalization, and secret redaction filters remain intact.

---

## 4. Responsible AI & Safety Guardrails

* **Action Allowlist:** Only operations in `{click, type, drag, wait, verify}` targeting active SAM 3.1 mask IDs are permitted.
* **Destructive Action Confirmation:** Steps marked `is_destructive=True` require explicit operator confirmation (`require_destructive_confirmation=True`).
* **Graceful Human Escalation:** If closed-loop verification fails after the retry and self-healing replan budget, the orchestrator halts safely and surfaces the diagnostic reason on the HUD.
