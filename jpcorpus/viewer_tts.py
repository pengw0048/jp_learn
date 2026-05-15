from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


VOICEVOX_BASE_URL = "http://127.0.0.1:50021"
DEFAULT_VOICEVOX_SPEAKER = 2
MAX_TTS_TEXT_LENGTH = 300


def voicevox_speakers(
    *,
    base_url: str = VOICEVOX_BASE_URL,
    timeout: float = 1.5,
) -> dict[str, Any]:
    payload = _read_json(f"{base_url.rstrip('/')}/speakers", timeout=timeout)
    speakers: list[dict[str, Any]] = []
    for speaker in payload if isinstance(payload, list) else []:
        name = str(speaker.get("name") or "").strip()
        styles = speaker.get("styles")
        if not name or not isinstance(styles, list):
            continue
        for style in styles:
            style_id = _speaker_id(style.get("id"))
            if style_id is None:
                continue
            style_name = str(style.get("name") or "").strip()
            label = f"{name} / {style_name}" if style_name else name
            speakers.append({"id": style_id, "label": label})
    return {"speakers": speakers}


def synthesize_voicevox(
    raw: dict[str, Any],
    *,
    base_url: str = VOICEVOX_BASE_URL,
    timeout: float = 20.0,
) -> bytes:
    text = _tts_text(raw.get("text"))
    speaker = _speaker_id(raw.get("speaker"))
    rate = _tts_rate(raw.get("rate"))
    if speaker is None:
        speaker = DEFAULT_VOICEVOX_SPEAKER
    base = base_url.rstrip("/")
    query = _read_json(
        f"{base}/audio_query?{urlencode({'text': text, 'speaker': speaker})}",
        data=b"",
        timeout=timeout,
    )
    if isinstance(query, dict):
        query["speedScale"] = rate
    request = Request(
        f"{base}/synthesis?{urlencode({'speaker': speaker})}",
        data=json.dumps(query, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def _read_json(url: str, *, data: bytes | None = None, timeout: float) -> Any:
    request = Request(url, data=data, method="POST" if data is not None else "GET")
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _tts_text(value: Any) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        raise ValueError("TTS text is empty.")
    if len(text) > MAX_TTS_TEXT_LENGTH:
        raise ValueError(f"TTS text is too long; keep it under {MAX_TTS_TEXT_LENGTH} characters.")
    return text


def _speaker_id(value: Any) -> int | None:
    try:
        speaker = int(value)
    except (TypeError, ValueError):
        return None
    return speaker if speaker >= 0 else None


def _tts_rate(value: Any) -> float:
    try:
        rate = float(value)
    except (TypeError, ValueError):
        return 1.0
    if not 0.5 <= rate <= 2.0:
        return 1.0
    return rate
