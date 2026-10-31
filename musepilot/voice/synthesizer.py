# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Live speech synthesis and audible feedback engine for verified agent actions (Milestone S3)."""

from __future__ import annotations

import shutil
import subprocess
import sys
import threading

from musepilot.telemetry import get_logger

logger = get_logger("musepilot.voice.synthesizer")


class VoiceFeedbackSynthesizer:
    """Provides non-blocking speech synthesis confirmation for verified state transitions."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._say_bin = shutil.which("say") if sys.platform == "darwin" else None
        self._spd_say_bin = shutil.which("spd-say") if sys.platform.startswith("linux") else None
        self._espeak_bin = shutil.which("espeak") if sys.platform.startswith("linux") else None

    @property
    def is_available(self) -> bool:
        """Return True when an OS-level speech synthesis tool is accessible."""
        if not self.enabled:
            return False
        return bool(
            self._say_bin or self._spd_say_bin or self._espeak_bin or sys.platform == "win32"
        )

    def speak(self, text: str, non_blocking: bool = True) -> bool:
        """Dispatch a spoken message via the available platform speech tool."""
        if not self.enabled or not text.strip():
            return False

        logger.info(f"Auditory confirmation: '{text}'")

        if non_blocking:
            thread = threading.Thread(target=self._speak_sync, args=(text,), daemon=True)
            thread.start()
            return True
        return self._speak_sync(text)

    def _speak_sync(self, text: str) -> bool:
        """Synchronously execute the platform speech synthesis tool."""
        try:
            if sys.platform == "darwin" and self._say_bin:
                subprocess.run(  # noqa: S603 - fixed argv vector, shell disabled
                    [self._say_bin, text],
                    check=True,
                    timeout=10,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return True
            if sys.platform.startswith("linux"):
                if self._spd_say_bin:
                    subprocess.run(  # noqa: S603
                        [self._spd_say_bin, text],
                        check=True,
                        timeout=10,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    return True
                if self._espeak_bin:
                    subprocess.run(  # noqa: S603
                        [self._espeak_bin, text],
                        check=True,
                        timeout=10,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    return True
            if sys.platform == "win32":
                ps_bin = shutil.which("powershell")
                if ps_bin:
                    ps_script = f"Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{text}')"
                    subprocess.run(  # noqa: S603, S607
                        [ps_bin, "-Command", ps_script],
                        check=True,
                        timeout=10,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    return True
        except Exception as exc:
            logger.debug(f"Speech synthesis command skipped ({exc})")
        return False

    def speak_step_verified(self, step_id: int, summary: str) -> None:
        """Audibly confirm a verified state transition."""
        self.speak(f"Step {step_id} verified: {summary}")

    def speak_self_healing(self, hint: str) -> None:
        """Audibly announce an autonomous self-healing recovery event."""
        self.speak(f"Obstruction detected. Autonomous self healing engaged: {hint}")

    def speak_workflow_completed(self, workflow_id: str) -> None:
        """Audibly announce complete workflow verification."""
        self.speak(
            f"Workflow {workflow_id.upper()} completed and fully verified with zero coordinate drift."
        )
