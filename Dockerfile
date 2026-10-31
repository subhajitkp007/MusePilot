# syntax=docker/dockerfile:1.7
# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0

# ==============================================================================
# Stage 1: Builder — Compile wheels and resolve dependencies in isolation
# ==============================================================================
FROM python:3.12-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install -r requirements.txt

# ==============================================================================
# Stage 2: Runtime — Minimal, rootless, security-hardened container
# ==============================================================================
FROM python:3.12-slim-bookworm AS runtime

LABEL org.opencontainers.image.title="MusePilot" \
      org.opencontainers.image.description="Zero-Coordinate, Visually-Verified Multimodal GUI Agent powered by Meta SAM 3.1 & Muse Models" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.vendor="MusePilot Team"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app" \
    MUSEPILOT_EXECUTION_MODE="simulated" \
    MUSEPILOT_LOG_FORMAT="json" \
    MUSEPILOT_TRACE_DIR="/app/traces" \
    MUSEPILOT_LOG_DIR="/app/logs"

# Create non-root user and group following container security best practices
RUN groupadd --gid 10001 musepilot && \
    useradd --uid 10001 --gid musepilot --shell /bin/bash --create-home musepilot

WORKDIR /app

# Copy isolated virtualenv from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy source code, prompts, configs, and demo assets
COPY --chown=musepilot:musepilot musepilot/ /app/musepilot/
COPY --chown=musepilot:musepilot prompts/ /app/prompts/
COPY --chown=musepilot:musepilot configs/ /app/configs/
COPY --chown=musepilot:musepilot demo/ /app/demo/
COPY --chown=musepilot:musepilot pyproject.toml README.md LICENSE /app/

# Create runtime directories with proper ownership
RUN mkdir -p /app/traces /app/logs && \
    chown -R musepilot:musepilot /app/traces /app/logs

USER musepilot

EXPOSE 8501

# Container-level healthcheck invoking MusePilot's pre-flight verification engine
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["python", "-m", "musepilot.health.checker", "--quiet"]

ENTRYPOINT ["python", "-m", "musepilot.cli"]
CMD ["--help"]

