# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""OpenTelemetry-compatible span tracer and quantitative metrics registry."""

from __future__ import annotations

import secrets
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from statistics import median
from typing import Any

from musepilot.telemetry.logger import get_logger
from musepilot.telemetry.redaction import redact_dict

logger = get_logger("musepilot.telemetry")


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
        self.end_time_ns = time.time_ns()
        self.duration_ms = round((self.end_time_ns - self.start_time_ns) / 1_000_000, 2)
        self.status = status

    def to_otel_dict(self) -> dict[str, Any]:
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


class TelemetryRegistry:
    """In-memory collector for spans, model latencies, and benchmark metrics."""

    def __init__(self) -> None:
        self.spans: list[TelemetrySpan] = []
        self.sam_latencies_ms: list[float] = []
        self.planner_latencies_ms: list[float] = []
        self.verifier_latencies_ms: list[float] = []

    def reset(self) -> None:
        self.spans.clear()
        self.sam_latencies_ms.clear()
        self.planner_latencies_ms.clear()
        self.verifier_latencies_ms.clear()

    @contextmanager
    def start_span(self, name: str, trace_id: str, **attributes: Any) -> Iterator[TelemetrySpan]:
        span = TelemetrySpan(name=name, trace_id=trace_id, attributes=dict(attributes))
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
        self.sam_latencies_ms.append(latency_ms)

    def record_planner_latency(self, latency_ms: float) -> None:
        self.planner_latencies_ms.append(latency_ms)

    def record_verifier_latency(self, latency_ms: float) -> None:
        self.verifier_latencies_ms.append(latency_ms)

    @property
    def median_sam_ms(self) -> float:
        return round(median(self.sam_latencies_ms), 2) if self.sam_latencies_ms else 0.0

    @property
    def median_planner_ms(self) -> float:
        return round(median(self.planner_latencies_ms), 2) if self.planner_latencies_ms else 0.0

    @property
    def median_verifier_ms(self) -> float:
        return round(median(self.verifier_latencies_ms), 2) if self.verifier_latencies_ms else 0.0


GLOBAL_TELEMETRY = TelemetryRegistry()
