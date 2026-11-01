# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Shared JSON repair helpers for live model replies."""

from __future__ import annotations

import json

from musepilot.contracts.schemas import LiveModelError


def extract_json_object(text: str) -> dict:
    """Extract the first JSON object from model text, tolerating fences and prose."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise LiveModelError("Model reply contained no JSON object.")
    try:
        parsed = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LiveModelError(f"Model reply was not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise LiveModelError("Model reply JSON was not an object.")
    return parsed
