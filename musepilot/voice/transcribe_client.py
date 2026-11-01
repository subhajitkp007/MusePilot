# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Voice command intake powered by Meta Muse Voice Transcribe."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx

from musepilot.config import get_settings
from musepilot.contracts.schemas import LiveModelError, VoiceTranscript
from musepilot.telemetry import GLOBAL_TELEMETRY, get_logger

logger = get_logger("musepilot.voice.transcribe")


def extract_transcript(payload: dict[str, Any]) -> str:
    """Extract transcript text from a TranscribeResponse payload."""
    for key in ("transcript", "text"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    turns = payload.get("turns")
    if isinstance(turns, list):
        parts = [t.get("transcript", "") for t in turns if isinstance(t, dict)]
        joined = " ".join(p.strip() for p in parts if p and p.strip())
        if joined:
            return joined
    results = payload.get("results")
    if isinstance(results, list):
        parts = [r.get("transcript", "") for r in results if isinstance(r, dict)]
        joined = " ".join(p.strip() for p in parts if p and p.strip())
        if joined:
            return joined
    raise LiveModelError("Transcribe response carried no transcript text.")


class MuseVoiceTranscribeClient:
    """Transcribes spoken operator commands into structured workflow intents."""

    DEFAULT_COMMANDS: dict[str, str] = {
        "w1": (
            "Calibrate the simulation parameters: set the frequency slider to 75 percent, "
            "enable adaptive damping, lock gain coefficient at 0.942, and run the benchmark."
        ),
        "w2": (
            "Extract today's system anomaly metrics from the monitoring console "
            "and dispatch an urgent incident report."
        ),
    }

    def __init__(self) -> None:
        self.settings = get_settings()

    def transcribe_command(
        self,
        workflow_id: str,
        audio_path: Path | None = None,
        trace_id: str = "local",
    ) -> VoiceTranscript:
        """Transcribe audio via Meta Muse Voice Transcribe API or return calibrated command."""
        with GLOBAL_TELEMETRY.start_span(
            "voice.muse_voice_transcribe",
            trace_id=trace_id,
            model_id=self.settings.voice_model_id,
            workflow_id=workflow_id,
        ):
            t0 = time.perf_counter()
            if self.settings.execution_mode == "live" and self.settings.meta_api_key:
                if audio_path is None or not audio_path.exists():
                    raise LiveModelError("Live voice intake requires an existing WAV audio file.")
                transcript_text = self._call_live_transcribe_api(audio_path)
            else:
                transcript_text = self.DEFAULT_COMMANDS.get(
                    workflow_id.lower(), self.DEFAULT_COMMANDS["w2"]
                )

            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            return VoiceTranscript(
                model_id=self.settings.voice_model_id,
                transcript=transcript_text,
                confidence=0.99,
                audio_duration_sec=3.1,
                latency_ms=latency_ms,
            )

    def _call_live_transcribe_api(self, audio_path: Path) -> str:
        """Transcribe a WAV recording via POST /v1/asr/transcribe."""
        if audio_path.suffix.lower() != ".wav":
            raise LiveModelError(
                f"Voice transcribe requires a WAV file, got '{audio_path.suffix}'."
            )
        settings_part = json.dumps(
            {
                "model": self.settings.voice_model_id,
                "audioEncoding": "WAV",
                "mode": "PUSH_TO_TALK",
            }
        )
        headers = {
            "Authorization": f"Bearer {self.settings.meta_api_key}",
            "Accept": "application/json",
        }
        try:
            with audio_path.open("rb") as audio_file:
                files = {
                    "request": (None, settings_part, "application/json"),
                    "audio": (audio_path.name, audio_file, "audio/wav"),
                }
                with httpx.Client(timeout=self.settings.api_timeout_seconds * 4) as client:
                    response = client.post(
                        f"{self.settings.meta_api_base_url.rstrip('/')}/asr/transcribe",
                        headers=headers,
                        files=files,
                    )
            response.raise_for_status()
            return extract_transcript(response.json())
        except httpx.HTTPStatusError as exc:
            raise LiveModelError(
                f"Voice transcribe rejected (HTTP {exc.response.status_code})."
            ) from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise LiveModelError(f"Voice transcribe failed: {exc}") from exc
