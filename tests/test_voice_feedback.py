# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Unit tests for live speech synthesis feedback engine (Milestone S3)."""

from __future__ import annotations

from musepilot.voice.synthesizer import VoiceFeedbackSynthesizer


def test_voice_feedback_disabled_returns_false() -> None:
    synth = VoiceFeedbackSynthesizer(enabled=False)
    assert synth.is_available is False
    assert synth.speak("test message") is False


def test_voice_feedback_methods_execute_safely(monkeypatch) -> None:
    synth = VoiceFeedbackSynthesizer(enabled=True)
    # Mock subprocess.run so speech doesn't actually play aloud in CI
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: None)
    monkeypatch.setattr(synth, "_say_bin", "/usr/bin/say")
    monkeypatch.setattr(synth, "_spd_say_bin", "/usr/bin/spd-say")
    monkeypatch.setattr(synth, "_espeak_bin", "/usr/bin/espeak")

    assert synth.speak("Step 1 verified", non_blocking=False) is True
    synth.speak_step_verified(1, "Frequency slider set to 75%")
    synth.speak_self_healing("Dismissing modal")
    synth.speak_workflow_completed("w1")
