# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Structured JSON and console logging with automatic PII/credential redaction."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from musepilot.config import get_settings
from musepilot.telemetry.redaction import RedactingLogFilter, redact_dict


class StructuredJsonFormatter(logging.Formatter):
    """Format log records as single-line structured JSON for observability pipelines."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "component": getattr(record, "component", "core"),
        }
        for extra_field in (
            "trace_id",
            "span_id",
            "workflow_id",
            "step_id",
            "mask_id",
            "model_id",
            "latency_ms",
            "verdict",
        ):
            val = getattr(record, extra_field, None)
            if val is not None:
                payload[extra_field] = val

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(redact_dict(payload), sort_keys=False)


def get_logger(name: str) -> logging.Logger:
    """Return a configured, redaction-protected logger instance."""
    settings = get_settings()
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, settings.log_level, logging.INFO))
    logger.propagate = False

    redacting_filter = RedactingLogFilter()

    # Stream handler (stdout)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.addFilter(redacting_filter)
    if settings.log_format == "json":
        stream_handler.setFormatter(StructuredJsonFormatter())
    else:
        stream_handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
                datefmt="%H:%M:%S",
            )
        )
    logger.addHandler(stream_handler)

    # Persistent JSONL file handler in logs/musepilot.jsonl
    try:
        settings.ensure_directories()
        file_handler = logging.FileHandler(settings.log_dir / "musepilot.jsonl", encoding="utf-8")
        file_handler.addFilter(redacting_filter)
        file_handler.setFormatter(StructuredJsonFormatter())
        logger.addHandler(file_handler)
    except OSError:
        # Gracefully continue with stdout if filesystem is read-only
        pass

    return logger
