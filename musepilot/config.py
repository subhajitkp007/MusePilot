# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Centralized, environment-driven configuration for MusePilot."""

from __future__ import annotations

import os
import warnings
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import Field, field_validator
from pydantic_settings import (
    BaseSettings,
    InitSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_YAML_PATH = PROJECT_ROOT / "configs" / "default_config.yaml"
CONFIG_YAML_PATH_ENV_VAR = "MUSEPILOT_CONFIG_YAML_PATH"

# Explicit mapping from nested YAML keys to flat MusePilotSettings fields.
# Only mapped keys are honored; anything else in the YAML is ignored.
_YAML_FIELD_MAP: tuple[tuple[tuple[str, ...], str], ...] = (
    (("models", "sam", "model_id"), "sam_model_id"),
    (("models", "planner", "model_id"), "planner_model_id"),
    (("models", "planner", "prompt_file"), "planner_prompt_path"),
    (("models", "planner", "temperature"), "planner_temperature"),
    (("models", "verifier", "model_id"), "verifier_model_id"),
    (("models", "verifier", "partner_name"), "partner_provider"),
    (("models", "verifier", "prompt_file"), "verifier_prompt_path"),
    (("models", "verifier", "min_roi_pixel_delta"), "verifier_min_roi_pixel_delta"),
    (("models", "verifier", "confidence_threshold"), "verifier_confidence_threshold"),
    (("models", "voice", "model_id"), "voice_model_id"),
    (("execution", "display_dpi_scale"), "display_dpi_scale"),
    (("execution", "max_retries_per_step"), "max_retries_per_step"),
    (("execution", "allow_replan_on_obstruction"), "allow_replan_on_obstruction"),
    (
        ("execution", "require_destructive_confirmation"),
        "require_destructive_confirmation",
    ),
    (("telemetry", "log_level"), "log_level"),
    (("telemetry", "log_format"), "log_format"),
)

_PATH_FIELDS = frozenset({"planner_prompt_path", "verifier_prompt_path"})


def resolve_yaml_path() -> Path:
    """Resolve the active YAML config path from the environment or the default."""
    override = os.environ.get(CONFIG_YAML_PATH_ENV_VAR)
    if override:
        return Path(override).expanduser()
    return DEFAULT_CONFIG_YAML_PATH


def _lookup_nested(data: dict[str, Any], keys: tuple[str, ...]) -> Any:
    """Return a nested mapping value or None when any level is absent."""
    node: Any = data
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node


def load_yaml_defaults(yaml_path: Path | None = None) -> dict[str, Any]:
    """Load flat settings defaults from the YAML config file (empty when unreadable)."""
    path = yaml_path or resolve_yaml_path()
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        data = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        warnings.warn(f"Ignoring invalid YAML config at {path}: {exc}", stacklevel=2)
        return {}
    if not isinstance(data, dict):
        return {}

    defaults: dict[str, Any] = {}
    for nested_keys, field_name in _YAML_FIELD_MAP:
        value = _lookup_nested(data, nested_keys)
        if value is None:
            continue
        if field_name in _PATH_FIELDS:
            candidate = Path(str(value)).expanduser()
            value = candidate if candidate.is_absolute() else PROJECT_ROOT / candidate
        defaults[field_name] = value
    return defaults


class YamlConfigSettingsSource(InitSettingsSource):
    """Expose YAML config values as the lowest-priority settings source."""

    def __init__(self, settings_cls: type[BaseSettings]) -> None:
        super().__init__(settings_cls, load_yaml_defaults())


class MusePilotSettings(BaseSettings):
    """Runtime settings loaded from environment variables or `.env` file."""

    model_config = SettingsConfigDict(
        env_prefix="MUSEPILOT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 1. Meta Model API Settings (SAM 3.1, Muse Spark, Muse Voice Transcribe)
    meta_api_key: str = Field(default="", description="Meta Model API Bearer [REDACTED]")
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
    planner_temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for live Muse Spark planner calls",
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
    verifier_min_roi_pixel_delta: float = Field(
        default=0.015,
        ge=0.0,
        le=1.0,
        description="Minimum ROI pixel-change ratio to accept a visual transition",
    )
    verifier_confidence_threshold: float = Field(
        default=0.80,
        ge=0.0,
        le=1.0,
        description="Minimum verifier confidence to pass a transition",
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
    adb_serial: str = Field(
        default="",
        description="Preferred adb device serial (empty selects the first attached device)",
    )
    allow_replan_on_obstruction: bool = Field(
        default=True,
        description="Self-heal via replan on obstruction; otherwise escalate to operator",
    )
    api_timeout_seconds: float = Field(default=15.0, gt=0.0)
    require_destructive_confirmation: bool = Field(default=True)

    # 4. Prompt Versioning Paths
    planner_prompt_path: Path = Field(default=PROJECT_ROOT / "prompts" / "planner_som_v1.txt")
    verifier_prompt_path: Path = Field(default=PROJECT_ROOT / "prompts" / "verifier_eval_v1.txt")
    config_yaml_path: Path = Field(
        default=DEFAULT_CONFIG_YAML_PATH,
        description="Active YAML defaults file (override via MUSEPILOT_CONFIG_YAML_PATH)",
    )

    # 5. Telemetry & Storage Paths
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    log_format: Literal["json", "console"] = Field(default="json")
    telemetry_enabled: bool = Field(default=True)
    otel_exporter_endpoint: str = Field(default="http://localhost:4318/v1/traces")
    trace_dir: Path = Field(default=PROJECT_ROOT / "traces")
    log_dir: Path = Field(default=PROJECT_ROOT / "logs")
    golden_trace_dir: Path = Field(default=PROJECT_ROOT / "demo" / "golden_traces")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Order sources: explicit init > env > dotenv > YAML file > secrets."""
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )

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
