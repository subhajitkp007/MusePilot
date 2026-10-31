# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""OpenTelemetry-compatible span tracer and quantitative metrics registry."""

from __future__ import annotations

import re
import secrets
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from statistics import median
from typing import Any

import httpx

from musepilot.config import get_settings
from musepilot.telemetry.logger import get_logger
from musepilot.telemetry.redaction import redact_dict

logger = get_logger("musepilot.telemetry")


def _normalize_hex_id(raw: str, width: int) -> str:
    """Pad a trace/span ID to fixed-width lowercase hex, zero-filling junk."""
    if re.fullmatch(r"[0-9a-fA-F]+", raw or ""):
        return raw.lower().rjust(width, "0")[-width:]
    return "0" * width


def _telemetry_enabled() -> bool:
    """Return True unless the operator disabled telemetry via settings."""
    return get_settings().telemetry_enabled


@dataclass
class TelemetrySpan:
    """Represents an OpenTelemetry-compatible execution span."""

    name: str
    trace_id: str
    span_id: str = field(default_factory=lambda: secrets.token_hex(8))
    start_time_ns: int = field(default_factory=time.time_ns)
    end_time_ns: int = 0
    duration_ms: float = 0.0
    status: str = "OK"
    attributes: dict[str, Any] = field(default_factory=dict)

    def finish(self, status: str = "OK") -> None:
        """Stamp span end time, duration, and status."""
        self.end_time_ns = time.time_ns()
        self.duration_ms = round((self.end_time_ns - self.start_time_ns) / 1_000_000, 2)
        self.status = status

    def to_otel_dict(self) -> dict[str, Any]:
        """Export the span as a redacted OTel-compatible dictionary."""
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "start_time_unix_nano": self.start_time_ns,
            "end_time_unix_nano": self.end_time_ns,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "attributes": redact_dict(self.attributes),
        }

    def to_otlp_span(self) -> dict[str, Any]:
        """Export the span in OTLP/HTTP JSON format for collectors like Jaeger."""
        attributes = [
            {"key": key, "value": {"stringValue": str(value)}}
            for key, value in redact_dict(self.attributes).items()
        ]
        return {
            "traceId": _normalize_hex_id(self.trace_id, 32),
            "spanId": _normalize_hex_id(self.span_id, 16),
            "name": self.name,
            "kind": 1,
            "startTimeUnixNano": str(self.start_time_ns),
            "endTimeUnixNano": str(self.end_time_ns or self.start_time_ns),
            "attributes": attributes,
            "status": {"code": 1 if self.status == "OK" else 2},
        }


class TelemetryRegistry:
    """In-memory collector for spans, model latencies, and benchmark metrics."""

    def __init__(self) -> None:
        self.spans: list[TelemetrySpan] = []
        self.sam_latencies_ms: list[float] = []
        self.planner_latencies_ms: list[float] = []
        self.verifier_latencies_ms: list[float] = []

    def reset(self) -> None:
        """Clear recorded spans and latency samples."""
        self.spans.clear()
        self.sam_latencies_ms.clear()
        self.planner_latencies_ms.clear()
        self.verifier_latencies_ms.clear()

    @contextmanager
    def start_span(self, name: str, trace_id: str, **attributes: Any) -> Iterator[TelemetrySpan]:
        """Record a span around the wrapped block and log its completion."""
        span = TelemetrySpan(name=name, trace_id=trace_id, attributes=dict(attributes))
        if not _telemetry_enabled():
            yield span
            return
        try:
            yield span
            span.finish("OK")
        except Exception as exc:
            span.attributes["error"] = str(exc)
            span.finish("ERROR")
            raise
        finally:
            self.spans.append(span)
            logger.info(
                f"Span completed: {name} ({span.duration_ms:.2f}ms) [{span.status}]",
                extra={
                    "trace_id": trace_id,
                    "span_id": span.span_id,
                    "component": name,
                    "latency_ms": span.duration_ms,
                    "model_id": span.attributes.get("model_id"),
                },
            )

    def record_sam_latency(self, latency_ms: float) -> None:
        """Append a SAM 3.1 latency sample in milliseconds."""
        if _telemetry_enabled():
            self.sam_latencies_ms.append(latency_ms)

    def record_planner_latency(self, latency_ms: float) -> None:
        """Append a planner latency sample in milliseconds."""
        if _telemetry_enabled():
            self.planner_latencies_ms.append(latency_ms)

    def record_verifier_latency(self, latency_ms: float) -> None:
        """Append a verifier latency sample in milliseconds."""
        if _telemetry_enabled():
            self.verifier_latencies_ms.append(latency_ms)

    def to_otlp_payload(self) -> dict[str, Any]:
        """Build an OTLP/HTTP JSON payload for the recorded spans."""
        return {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": "musepilot-agent"}}
                        ]
                    },
                    "scopeSpans": [
                        {
                            "scope": {"name": "musepilot"},
                            "spans": [span.to_otlp_span() for span in self.spans],
                        }
                    ],
                }
            ]
        }

    def export_otlp(self, endpoint: str | None = None) -> bool:
        """POST recorded spans to an OTLP/HTTP collector; return False on any failure."""
        if not _telemetry_enabled():
            return False
        url = endpoint or get_settings().otel_exporter_endpoint
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.post(url, json=self.to_otlp_payload())
            return 200 <= response.status_code < 300
        except Exception as exc:
            logger.warning(f"OTLP export to {url} failed ({exc}); continuing without export.")
            return False

    @property
    def median_sam_ms(self) -> float:
        """Return the median SAM 3.1 latency in milliseconds."""
        return round(median(self.sam_latencies_ms), 2) if self.sam_latencies_ms else 0.0

    @property
    def median_planner_ms(self) -> float:
        """Return the median planner latency in milliseconds."""
        return round(median(self.planner_latencies_ms), 2) if self.planner_latencies_ms else 0.0

    @property
    def median_verifier_ms(self) -> float:
        """Return the median verifier latency in milliseconds."""
        return round(median(self.verifier_latencies_ms), 2) if self.verifier_latencies_ms else 0.0


GLOBAL_TELEMETRY = TelemetryRegistry()
