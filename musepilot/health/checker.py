# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Pre-flight environment, model compliance, and display calibration checker."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass

from musepilot.config import get_settings


@dataclass(frozen=True)
class HealthCheckReport:
    """Structured pre-flight health check report."""

    passed: bool
    execution_mode: str
    sam_model_id: str
    planner_model_id: str
    verifier_model_id: str
    partner_provider: str
    voice_model_id: str
    display_dpi_scale: float
    config_yaml_path: str
    config_yaml_present: bool
    prompts_verified: bool
    directories_writable: bool
    api_keys_configured: bool
    checks: dict[str, bool]


def run_health_check() -> HealthCheckReport:
    """Execute all pre-flight readiness checks for MusePilot."""
    settings = get_settings()
    settings.ensure_directories()

    prompts_ok = settings.planner_prompt_path.exists() and settings.verifier_prompt_path.exists()
    yaml_ok = settings.config_yaml_path.exists()
    dirs_ok = settings.trace_dir.is_dir() and settings.log_dir.is_dir()
    open_weight_ok = settings.verifier_model_id.startswith(
        ("meta-models/muse-spark-open", "meta-models/muse-glimmer")
    )
    dpi_ok = 0.5 <= settings.display_dpi_scale <= 4.0
    keys_configured = bool(settings.meta_api_key or settings.partner_api_key)

    checks = {
        "versioned_prompts_exist": prompts_ok,
        "config_yaml_present": yaml_ok,
        "storage_directories_writable": dirs_ok,
        "open_weight_bonus_model_valid": open_weight_ok,
        "display_dpi_scale_calibrated": dpi_ok,
        "mode_ready": (keys_configured if settings.execution_mode == "live" else True),
    }

    overall_passed = all(checks.values())
    return HealthCheckReport(
        passed=overall_passed,
        execution_mode=settings.execution_mode,
        sam_model_id=settings.sam_model_id,
        planner_model_id=settings.planner_model_id,
        verifier_model_id=settings.verifier_model_id,
        partner_provider=settings.partner_provider,
        voice_model_id=settings.voice_model_id,
        display_dpi_scale=settings.display_dpi_scale,
        config_yaml_path=str(settings.config_yaml_path),
        config_yaml_present=yaml_ok,
        prompts_verified=prompts_ok,
        directories_writable=dirs_ok,
        api_keys_configured=keys_configured,
        checks=checks,
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for `python -m musepilot.health.checker`."""
    parser = argparse.ArgumentParser(description="MusePilot Pre-Flight Health Check")
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose output")
    args = parser.parse_args(argv)

    report = run_health_check()
    if not args.quiet:
        print(json.dumps(asdict(report), indent=2))
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
