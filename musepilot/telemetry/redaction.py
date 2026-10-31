# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Automatic PII, credential, and sensitive-field redaction filters."""

from __future__ import annotations

import logging
import re
from typing import Any

REDACTED_TOKEN = "[REDACTED]"  # noqa: S105

# Compiled regex patterns for secret tokens, API keys, and bearer headers
SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(Bearer\s+)[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
    re.compile(r"\b(sk-[A-Za-z0-9]{16,})\b"),
    re.compile(r"(api[_-]?key\s*[:=]\s*['\"]?)([A-Za-z0-9\-._~+/]{12,})(['\"]?)", re.IGNORECASE),
    re.compile(r"(password\s*[:=]\s*['\"]?)([^\s'\"]+)(['\"]?)", re.IGNORECASE),
    re.compile(r"(token\s*[:=]\s*['\"]?)([A-Za-z0-9\-._~+/]{12,})(['\"]?)", re.IGNORECASE),
)

SENSITIVE_DICT_KEYS = frozenset(
    {
        "api_key",
        "meta_api_key",
        "partner_api_key",
        "password",
        "secret",
        "token",
        "authorization",
        "credential",
    }
)


def redact_text(text: str | None) -> str | None:
    """Scrub API keys, bearer tokens, and passwords from a string."""
    if not text:
        return text
    scrubbed = text
    scrubbed = SECRET_PATTERNS[0].sub(rf"\1{REDACTED_TOKEN}", scrubbed)
    scrubbed = SECRET_PATTERNS[1].sub(REDACTED_TOKEN, scrubbed)
    scrubbed = SECRET_PATTERNS[2].sub(rf"\1{REDACTED_TOKEN}\3", scrubbed)
    scrubbed = SECRET_PATTERNS[3].sub(rf"\1{REDACTED_TOKEN}\3", scrubbed)
    scrubbed = SECRET_PATTERNS[4].sub(rf"\1{REDACTED_TOKEN}\3", scrubbed)
    return scrubbed


def redact_step_value(value: str | None, *, is_sensitive: bool = False) -> str | None:
    """Redact step input payload if flagged sensitive or containing secrets."""
    if value is None:
        return None
    if is_sensitive:
        return REDACTED_TOKEN
    return redact_text(value)


def redact_dict(payload: dict[str, Any]) -> dict[str, Any]:
    """Recursively redact sensitive keys and string values in a dictionary."""
    sanitized: dict[str, Any] = {}
    is_marked_sensitive = bool(payload.get("is_sensitive", False))
    for key, val in payload.items():
        if key.lower() in SENSITIVE_DICT_KEYS:
            sanitized[key] = REDACTED_TOKEN
        elif key == "input_value" and is_marked_sensitive and val is not None:
            sanitized[key] = REDACTED_TOKEN
        elif isinstance(val, dict):
            sanitized[key] = redact_dict(val)
        elif isinstance(val, list):
            sanitized[key] = [
                redact_dict(item)
                if isinstance(item, dict)
                else (redact_text(item) if isinstance(item, str) else item)
                for item in val
            ]
        elif isinstance(val, str):
            sanitized[key] = redact_text(val)
        else:
            sanitized[key] = val
    return sanitized


class RedactingLogFilter(logging.Filter):
    """Logging filter that guarantees no secret or sensitive value reaches handlers."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_text(record.msg) or ""
        if record.args:
            if isinstance(record.args, dict):
                record.args = redact_dict(record.args)
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    redact_text(arg) if isinstance(arg, str) else arg for arg in record.args
                )
        return True
