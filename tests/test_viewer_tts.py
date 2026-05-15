from __future__ import annotations

import json
from urllib.parse import parse_qs, urlparse

import pytest

from jpcorpus.viewer_tts import synthesize_voicevox, voicevox_speakers


class FakeResponse:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.content


def test_voicevox_speakers_flattens_speaker_styles(monkeypatch: pytest.MonkeyPatch):
    raw = [
        {
            "name": "四国めたん",
            "styles": [
                {"id": 2, "name": "ノーマル"},
                {"id": 0, "name": "あまあま"},
            ],
        },
        {"name": "", "styles": [{"id": 99, "name": "ignored"}]},
        {"name": "broken", "styles": [{"name": "missing id"}]},
    ]

    def fake_urlopen(request, timeout: float):  # noqa: ANN001
        assert request.full_url == "http://voicevox.test/speakers"
        assert timeout == 0.5
        return FakeResponse(json.dumps(raw).encode("utf-8"))

    monkeypatch.setattr("jpcorpus.viewer_tts.urlopen", fake_urlopen)

    assert voicevox_speakers(base_url="http://voicevox.test", timeout=0.5) == {
        "speakers": [
            {"id": 2, "label": "四国めたん / ノーマル"},
            {"id": 0, "label": "四国めたん / あまあま"},
        ],
    }


def test_synthesize_voicevox_posts_query_then_synthesis(monkeypatch: pytest.MonkeyPatch):
    calls = []

    def fake_urlopen(request, timeout: float):  # noqa: ANN001
        calls.append({
            "url": request.full_url,
            "method": request.get_method(),
            "data": request.data,
            "timeout": timeout,
            "headers": dict(request.header_items()),
        })
        if request.full_url.startswith("http://voicevox.test/audio_query?"):
            return FakeResponse(json.dumps({"accent_phrases": []}).encode("utf-8"))
        return FakeResponse(b"RIFFfake-wave")

    monkeypatch.setattr("jpcorpus.viewer_tts.urlopen", fake_urlopen)

    audio = synthesize_voicevox(
        {"text": "  こんにちは\n世界  ", "speaker": "8", "rate": "1.25"},
        base_url="http://voicevox.test/",
        timeout=3.0,
    )

    assert audio == b"RIFFfake-wave"
    assert len(calls) == 2
    assert calls[0]["method"] == "POST"
    assert parse_qs(urlparse(calls[0]["url"]).query) == {
        "text": ["こんにちは 世界"],
        "speaker": ["8"],
    }
    assert calls[1]["method"] == "POST"
    assert parse_qs(urlparse(calls[1]["url"]).query) == {"speaker": ["8"]}
    assert calls[1]["headers"]["Content-type"] == "application/json"
    assert json.loads(calls[1]["data"].decode("utf-8"))["speedScale"] == 1.25
    assert calls[0]["timeout"] == 3.0
    assert calls[1]["timeout"] == 3.0


def test_synthesize_voicevox_rejects_empty_or_long_text():
    with pytest.raises(ValueError, match="empty"):
        synthesize_voicevox({"text": ""})

    with pytest.raises(ValueError, match="too long"):
        synthesize_voicevox({"text": "あ" * 301})
