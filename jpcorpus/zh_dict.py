from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from .paths import DEFAULT_ZH_DICT, ensure_parent


DEFAULT_ZH_DICT_URL = (
    "https://raw.githubusercontent.com/lxl66566/"
    "Japanese-Chinese-thesaurus/main/final.json"
)
CHINESE_GLOSS_OVERRIDES = {
    "ありがとう": "谢谢",
    "有難う": "谢谢",
    "有り難う": "谢谢",
    "おはよう": "早上好",
    "お早う": "早上好",
    "こんにちは": "你好；午安",
    "こんばんは": "晚上好",
    "ごめんなさい": "对不起；不好意思",
    "すみません": "不好意思；对不起；劳驾",
    "さようなら": "再见",
    "いただきます": "我开动了；饭前致谢",
    "ごちそうさま": "多谢款待；我吃好了",
    "お休み": "晚安；休息",
    "おやすみ": "晚安；休息",
}


@dataclass(frozen=True)
class ChineseGlossary:
    entries: dict[str, str]
    readings: dict[str, tuple[str, ...]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path = DEFAULT_ZH_DICT) -> "ChineseGlossary":
        if not path.exists():
            return cls({})
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Chinese glossary must be a JSON object: {path}")
        entries: dict[str, str] = {}
        readings: dict[str, tuple[str, ...]] = {}
        for key, value in payload.items():
            key_text = str(key)
            value_text = str(value)
            entries[key_text] = clean_gloss(value_text)
            entry_readings = extract_gloss_readings(value_text)
            if entry_readings:
                readings[key_text] = entry_readings
        entries.update(CHINESE_GLOSS_OVERRIDES)
        for key in CHINESE_GLOSS_OVERRIDES:
            readings.pop(key, None)
        return cls(entries, readings)

    def lookup(self, *keys: str | None, reading: str | None = None) -> str | None:
        for key in keys:
            if not key:
                continue
            gloss = self.entries.get(key)
            if gloss:
                expected_readings = self.readings.get(key)
                if expected_readings and reading and not readings_match(reading, expected_readings):
                    continue
                return gloss
        return None


def download_zh_dict(
    path: Path = DEFAULT_ZH_DICT,
    *,
    source_url: str = DEFAULT_ZH_DICT_URL,
    timeout: float = 60.0,
) -> Path:
    ensure_parent(path)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.get(source_url)
        response.raise_for_status()
    payload: Any = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Downloaded Chinese glossary is not a JSON object.")
    normalized = {str(key): normalize_gloss_source(str(value)) for key, value in payload.items()}
    path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def normalize_gloss_source(value: str) -> str:
    value = value.replace("\\n", " ")
    return re.sub(r"\s+", " ", value).strip()


def extract_gloss_readings(value: str) -> tuple[str, ...]:
    value = normalize_gloss_source(value)
    match = re.match(r"^[（(]([ぁ-んァ-ンー・\s0-9０-９⓪①②③④⑤⑥⑦⑧⑨/／;；]+)[）)]", value)
    if not match:
        return ()
    return split_readings(match.group(1))


def readings_match(reading: str, expected_readings: tuple[str, ...]) -> bool:
    normalized = set(split_readings(reading))
    expected = {katakana_to_hiragana(value) for value in expected_readings}
    return bool(normalized & expected)


def split_readings(value: str) -> tuple[str, ...]:
    readings: list[str] = []
    for item in re.split(r"[/／;；]", value):
        cleaned = re.sub(r"[0-9０-９⓪①②③④⑤⑥⑦⑧⑨\s]+", "", item)
        if cleaned:
            readings.append(katakana_to_hiragana(cleaned))
    return tuple(dict.fromkeys(readings))


def katakana_to_hiragana(value: str) -> str:
    return "".join(
        chr(ord(char) - 0x60) if "ァ" <= char <= "ヶ" else char
        for char in str(value or "")
    )


def clean_gloss(value: str) -> str:
    value = normalize_gloss_source(value)
    value = re.sub(r"^[（(][ぁ-んァ-ンー・\s0-9０-９⓪①②③④⑤⑥⑦⑧⑨/／;；]+[）)]\s*", "", value)
    return value
