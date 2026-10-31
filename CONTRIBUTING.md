# Contributing to MusePilot

Welcome to **MusePilot**! We want to make contributing to this project as easy and transparent as possible, following [Meta Open Source](https://opensource.fb.com/) engineering and community standards.

---

## Table of Contents

1. [Code of Conduct](#1-code-of-conduct)
2. [Our Development Process (Summary + Test Plan)](#2-our-development-process-summary--test-plan)
3. [Developer Environment Setup](#3-developer-environment-setup)
4. [Pull Request Lifecycle](#4-pull-request-lifecycle)
5. [Coding Style & Architectural Invariants](#5-coding-style--architectural-invariants)
6. [Reporting Bugs & Security Issues](#6-reporting-bugs--security-issues)
7. [License & Contribution Terms](#7-license--contribution-terms)

---

## 1. Code of Conduct

This project adheres to our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code and foster an open, welcoming, and inclusive engineering environment.

---

## 2. Our Development Process (Summary + Test Plan)

We work directly on GitHub using small, atomic, well-tested Pull Requests inspired by Meta's engineering culture:
- **Every PR must include a clear `Summary` and an executable `Test Plan`.** A PR without reproducible verification evidence (`pytest` output, `make health` output, or a recorded trace ID) will not be merged.
- **`main` is always healthy:** Every commit on `main` must pass linting, security scanning, pre-flight calibration checks, and the full golden-trace fixture test suite.

---

## 3. Developer Environment Setup

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/<your-username>/MusePilot.git
   cd MusePilot
   ```
2. **Initialize the isolated virtual environment (`.venv`):**
   ```bash
   make setup
   cp .env.example .env
   ```
   > **Note:** Never run `pip install` globally. Always use `.venv/bin/pip` or the provided `Makefile` targets.
3. **Verify environment readiness:**
   ```bash
   make health
   make lint
   make test
   ```

---

## 4. Pull Request Lifecycle

1. **Create a topic branch** from `main`:
   ```bash
   git checkout -b feat/<component>-<short-description>
   ```
2. **Add or update unit and fixture tests** in [`tests/`](tests/) covering your change.
3. **Ensure every new source file includes the Apache-2.0 license header:**
   ```python
   # Copyright 2026 MusePilot Authors
   # Licensed under the Apache License, Version 2.0
   ```
4. **Run the full quality gate locally before pushing:**
   ```bash
   make format
   make lint
   make test
   make health
   ```
5. **Follow the structured commit message standard:**
   ```text
   <component>: <concise imperative summary>

   Evidence: <how this was tested or verified>
   Milestone: <M1-M9 / S1-S3>
   ```
6. **Open a Pull Request** completing all sections of [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md), including the **Summary** and **Test Plan**.

---

## 5. Coding Style & Architectural Invariants

All contributions must strictly preserve MusePilot's core architectural contracts:

### A. Python Style & Static Analysis
- **Python Version:** Python `>=3.10` with full type annotations (`from __future__ import annotations`).
- **Linter & Formatter:** Enforced via `ruff` (`line-length = 100`, `pycodestyle`, `pyflakes`, `isort`, `flake8-bugbear`, `pyupgrade`, `flake8-bandit` security rules).
- **Data Contracts:** All cross-component payloads must be defined as immutable or strictly validated `Pydantic v2` models in [`musepilot/contracts/schemas.py`](musepilot/contracts/schemas.py).

### B. The 5 Non-Negotiable Architectural Invariants
1. **Zero-Coordinate Invariant:**  
   Planner prompts, schemas, and outputs must **never** emit or accept raw `[x, y]` pixel coordinates (`x`, `y`, `coords`, `bbox`, `point`). All UI actions must reference a 1-indexed `target_mask_id` produced by Meta **SAM 3.1** (`meta-models/sam-3.1`).
2. **DPI Scale Normalization:**  
   All frame-space mask centroids must be translated to logical OS points via `translate_frame_px_to_os_logical(centroid_px, dpi_scale)` to guarantee accuracy across macOS Retina (`2.0x`) and standard (`1.0x`) displays.
3. **Closed-Loop Visual Verification:**  
   Every state-mutating action must be gated by [`SparkOpenVerifier`](musepilot/verification/spark_open_verifier.py) (`meta-models/muse-spark-open-1026` + ROI pixel delta) before the orchestrator advances the DAG.
4. **Versioned Prompt Files:**  
   Never hardcode system prompts in Python modules. Store all prompts in [`prompts/`](prompts/) with explicit version identifiers (e.g., `prompts/planner_som_v1.txt`).
5. **Structured Telemetry & Automatic Redaction:**  
   Use [`get_logger()`](musepilot/telemetry/logger.py) and [`GLOBAL_TELEMETRY.start_span()`](musepilot/telemetry/metrics.py) for all external calls. Never log raw credentials or unredacted sensitive step inputs.

---

## 6. Reporting Bugs & Security Issues

- **Bug Reports:** Open a GitHub Issue using the [Bug Report Template](.github/ISSUE_TEMPLATE/bug_report.yml) and include:
  - Output of `make health`
  - The recorded `trace_id` or JSON trace snippet
  - Display DPI scale and OS version
- **Security Vulnerabilities:** Please do **not** file public GitHub issues for security vulnerabilities or credential leaks. Refer to [`SECURITY.md`](SECURITY.md) for responsible disclosure instructions.

---

## 7. License & Contribution Terms

By contributing to **MusePilot**, you agree that your contributions will be licensed under the [Apache License, Version 2.0](LICENSE) as detailed in the root `LICENSE` file.
