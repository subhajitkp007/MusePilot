# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Unit tests for PII/secret redaction and OpenTelemetry span tracking."""

from __future__ import annotations

from musepilot.telemetry import (
    GLOBAL_TELEMETRY,
    REDACTED_TOKEN,
    redact_dict,
    redact_step_value,
    redact_text,
)


def test_redact_text_scrubs_tokens_and_keys() -> None:
    raw = "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.fake.signature0123 and key sk-faketestkey1234567"
    scrubbed = redact_text(raw)
    assert scrubbed is not None
    assert "eyJhbGci" not in scrubbed
    assert "sk-faketestkey1234567" not in scrubbed
    assert REDACTED_TOKEN in scrubbed


def test_redact_step_value_handles_sensitive_flag() -> None:
    assert redact_step_value("super-secret-password", is_sensitive=True) == REDACTED_TOKEN
    assert redact_step_value("0.942", is_sensitive=False) == "0.942"


def test_redact_dict_recursively_sanitizes_payloads() -> None:
    payload = {
        "meta_api_key": "secret_meta_token_value",
        "nested": {
            "step_id": 2,
            "input_value": "my_private_passcode",
            "is_sensitive": True,
        },
        "normal_field": "visible_value",
    }
    cleaned = redact_dict(payload)
    assert cleaned["meta_api_key"] == REDACTED_TOKEN
    assert cleaned["nested"]["input_value"] == REDACTED_TOKEN
    assert cleaned["normal_field"] == "visible_value"


def test_telemetry_span_recording() -> None:
    GLOBAL_TELEMETRY.reset()
    with GLOBAL_TELEMETRY.start_span(
        "test.component", trace_id="trace001", model_id="meta-models/sam-3.1"
    ):
        GLOBAL_TELEMETRY.record_sam_latency(14.5)

    assert len(GLOBAL_TELEMETRY.spans) == 1
    span_dict = GLOBAL_TELEMETRY.spans[0].to_otel_dict()
    assert span_dict["name"] == "test.component"
    assert span_dict["status"] == "OK"
    assert GLOBAL_TELEMETRY.median_sam_ms == 14.5


def test_redact_text_scrubs_hyphenated_api_keys() -> None:
    raw = "key=sk-ant-fake-test-0123456789abcdef"
    scrubbed = redact_text(raw)
    assert scrubbed is not None
    assert "sk-ant-fake-test" not in scrubbed
    assert REDACTED_TOKEN in scrubbed
