# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Centralized, environment-driven configuration for MusePilot."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class MusePilotSettings(BaseSettings):
    """Runtime settings loaded from environment variables or `.env` file."""

    model_config = SettingsConfigDict(
        env_prefix="MUSEPILOT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 1. Meta Model API Settings (SAM 3.1, Muse Spark, Muse Voice Transcribe)
    meta_api_key: str = Field(default="", description="Meta Model API bearer token")
    meta_api_base_url: str = Field(
        default="https://api.meta.ai/v1",
        description="Meta Model API base URL",
    )
    sam_model_id: str = Field(
        default="meta-models/sam-3.1",
        description="SAM 3.1 segmentation model identifier",
    )
    planner_model_id: str = Field(
        default="meta-models/muse-spark",
        description="Muse Spark multimodal planner model identifier",
    )
    voice_model_id: str = Field(
        default="meta-models/muse-voice-transcribe",
        description="Muse Voice Transcribe model identifier",
    )

    # 2. Partner Inference Open-Weight Verifier ($10K Bonus Qualification)
    partner_provider: Literal["baseten", "modal", "fireworks"] = Field(
        default="baseten",
        description="Partner inference provider hosting Meta open-weight verifier",
    )
    partner_api_key: str = Field(default="", description="Partner inference API key")
    partner_base_url: str = Field(
        default="https://inference.baseten.co/v1",
        description="Partner inference OpenAI-compatible base URL",
    )
    verifier_model_id: str = Field(
        default="meta-models/muse-spark-open-1026",
        description="Official hackathon open-weight model ID for verification",
    )

    # 3. Execution, Display & Guardrails
    display_dpi_scale: float = Field(
        default=2.0,
        gt=0.0,
        le=4.0,
        description="Physical-to-logical pixel ratio (e.g., 2.0 for macOS Retina)",
    )
    execution_mode: Literal["simulated", "live"] = Field(
        default="simulated",
        description="Execution mode: 'simulated' (deterministic canvas) or 'live' (API + OS)",
    )
    max_retries_per_step: int = Field(default=2, ge=0, le=5)
    api_timeout_seconds: float = Field(default=15.0, gt=0.0)
    require_destructive_confirmation: bool = Field(default=True)

    # 4. Prompt Versioning Paths
    planner_prompt_path: Path = Field(default=PROJECT_ROOT / "prompts" / "planner_som_v1.txt")
    verifier_prompt_path: Path = Field(default=PROJECT_ROOT / "prompts" / "verifier_eval_v1.txt")

    # 5. Telemetry & Storage Paths
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    log_format: Literal["json", "console"] = Field(default="json")
    telemetry_enabled: bool = Field(default=True)
    otel_exporter_endpoint: str = Field(default="http://localhost:4318/v1/traces")
    trace_dir: Path = Field(default=PROJECT_ROOT / "traces")
    log_dir: Path = Field(default=PROJECT_ROOT / "logs")
    golden_trace_dir: Path = Field(default=PROJECT_ROOT / "demo" / "golden_traces")

    @field_validator("verifier_model_id")
    @classmethod
    def validate_open_weight_model(cls, value: str) -> str:
        """Ensure open-weight verifier references an official Meta open model."""
        allowed_prefixes = ("meta-models/muse-spark-open", "meta-models/muse-glimmer")
        if not value.startswith(allowed_prefixes):
            raise ValueError(
                f"verifier_model_id '{value}' must be a Meta open-weight model "
                f"({', '.join(allowed_prefixes)}) to qualify for the Open Weight Bonus."
            )
        return value

    def ensure_directories(self) -> None:
        """Create trace and log directories if they do not exist."""
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.golden_trace_dir.mkdir(parents=True, exist_ok=True)


def get_settings() -> MusePilotSettings:
    """Return a validated MusePilotSettings instance."""
    settings = MusePilotSettings()
    settings.ensure_directories()
    return settings
