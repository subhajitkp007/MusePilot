# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Focused tests for live voice transcription parsing and the audio endpoint."""

from __future__ import annotations

import os
from pathlib import Path

import httpx
import pytest
from starlette.testclient import TestClient

from musepilot.contracts.schemas import LiveModelError
from musepilot.server.app import create_app
from musepilot.voice.transcribe_client import (
    MuseVoiceTranscribeClient,
    extract_transcript,
)

client = TestClient(create_app())
client.get("/api/auth/token")


def test_extract_transcript_reads_shapes() -> None:
    """Transcript extraction tolerates transcript/text/turns/results shapes."""
    assert extract_transcript({"transcript": "hello"}) == "hello"
    assert extract_transcript({"text": "hi"}) == "hi"
    assert extract_transcript({"turns": [{"transcript": "a"}, {"transcript": "b"}]}) == "a b"
    assert extract_transcript({"results": [{"transcript": "c"}]}) == "c"
    with pytest.raises(LiveModelError, match="no transcript"):
        extract_transcript({"sessionId": "abc"})


def test_live_transcribe_rejects_non_wav(tmp_path: Path) -> None:
    """Non-WAV audio fails closed before any network call."""
    audio = tmp_path / "command.mp3"
    audio.write_bytes(b"ID3")
    with pytest.raises(LiveModelError, match="requires a WAV file"):
        MuseVoiceTranscribeClient()._call_live_transcribe_api(audio)


def test_live_transcribe_posts_multipart_shape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The live call sends request-JSON + audio parts to /asr/transcribe."""
    audio = tmp_path / "command.wav"
    audio.write_bytes(b"RIFF....WAVE")
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["accept"] = request.headers.get("Accept")
        body = request.content.decode("latin-1")
        seen["has_request_part"] = 'name="request"' in body
        seen["has_audio_part"] = 'name="audio"' in body
        seen["has_model"] = "muse-voice-transcribe-1.0" in body
        return httpx.Response(200, json={"transcript": "open the pod bay doors"})

    real_client = httpx.Client
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: real_client(transport=transport, **kwargs)
    )
    text = MuseVoiceTranscribeClient()._call_live_transcribe_api(audio)
    assert text == "open the pod bay doors"
    assert seen["path"] == "/v1/asr/transcribe"
    assert seen["accept"] == "application/json"
    assert seen["has_request_part"] and seen["has_audio_part"] and seen["has_model"]


def test_live_transcribe_requires_audio_file(tmp_path: Path) -> None:
    """Live mode without an audio file raises instead of using canned text."""
    from musepilot.config import MusePilotSettings

    settings = MusePilotSettings(execution_mode="live", meta_api_key="test-key")
    voice_client = MuseVoiceTranscribeClient()
    voice_client.settings = settings
    with pytest.raises(LiveModelError, match="requires an existing WAV"):
        voice_client.transcribe_command("w2", audio_path=None, trace_id="test")
    with pytest.raises(LiveModelError, match="requires an existing WAV"):
        voice_client.transcribe_command("w2", audio_path=tmp_path / "missing.wav", trace_id="test")


def test_voice_endpoint_serves_simulated_transcript(tmp_path: Path) -> None:
    """POST /api/voice/transcribe accepts WAV and returns a transcript."""
    audio = tmp_path / "command.wav"
    audio.write_bytes(b"RIFF....WAVE")
    with audio.open("rb") as handle:
        response = client.post(
            "/api/voice/transcribe",
            files={"audio": ("command.wav", handle, "audio/wav")},
            data={"workflow_id": "w2"},
        )
    assert response.status_code == 200
    body = response.json()
    assert "anomaly" in body["transcript"].lower()
    assert body["model_id"] == "muse-voice-transcribe-1.0"


def test_voice_endpoint_validates_upload(tmp_path: Path) -> None:
    """The voice endpoint rejects missing audio, non-WAV, and bad workflows."""
    assert client.post("/api/voice/transcribe", data={}).status_code == 400
    audio = tmp_path / "command.mp3"
    audio.write_bytes(b"ID3")
    with audio.open("rb") as handle:
        response = client.post(
            "/api/voice/transcribe", files={"audio": ("command.mp3", handle, "audio/mpeg")}
        )
    assert response.status_code == 400
    wav = tmp_path / "command.wav"
    wav.write_bytes(b"RIFF....WAVE")
    with wav.open("rb") as handle:
        response = client.post(
            "/api/voice/transcribe",
            files={"audio": ("command.wav", handle, "audio/wav")},
            data={"workflow_id": "w9"},
        )
    assert response.status_code == 400


@pytest.mark.skipif(
    not os.environ.get("MUSEPILOT_LIVE_TESTS"), reason="Live API test (costs credits)"
)
def test_live_voice_wire_transcribes(tmp_path: Path) -> None:
    """Live: spoken W2 command transcribes to matching text."""
    from musepilot.config import MusePilotSettings

    dotenv = Path(__file__).resolve().parent.parent / ".env"
    key = ""
    if dotenv.exists():
        for line in dotenv.read_text(encoding="utf-8").splitlines():
            if line.startswith("MUSEPILOT_META_API_KEY="):
                key = line.split("=", 1)[1].strip()
    assert key, "MUSEPILOT_META_API_KEY required for live tests"
    fixture = Path(__file__).parent / "fixtures" / "voice_command.wav"
    assert fixture.exists(), "Generate fixtures/voice_command.wav first (see app docs)"
    settings = MusePilotSettings(execution_mode="live", meta_api_key=key)
    voice_client = MuseVoiceTranscribeClient()
    voice_client.settings = settings
    transcript = voice_client.transcribe_command("w2", audio_path=fixture, trace_id="test")
    assert "anomaly" in transcript.transcript.lower()
