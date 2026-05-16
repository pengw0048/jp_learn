from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any, Iterable

import httpx

from .models import WordEntry
from .paths import ensure_parent


WORD_KEYS = ("word", "surface", "kanji", "expression", "term", "vocab", "text")
READING_KEYS = ("reading", "kana", "furigana", "pronunciation")
LEVEL_KEYS = ("level", "jlpt", "jlpt_level")
TAG_KEYS = ("tags", "tag")
MEANING_KEYS = ("meaning", "translation", "gloss", "english", "zh")
JLPT_ENTRY_OVERRIDES: dict[str, dict[str, object]] = {
    "言う": {"level": 5, "reading": "いう", "meaning": "to say"},
    "行く": {"level": 5, "reading": "いく; ゆく", "meaning": "to go"},
    "見る": {"level": 5, "reading": "みる", "meaning": "to see; to watch"},
    "来る": {"level": 5, "reading": "くる", "meaning": "to come"},
    "良い": {"level": 5, "reading": "よい; いい", "meaning": "good"},
    "ありがとう": {"level": 5, "meaning": "thank you"},
    "おはよう": {"level": 5, "meaning": "good morning"},
    "こんにちは": {"level": 5, "meaning": "hello, good day"},
    "こんばんは": {"level": 5, "meaning": "good evening"},
    "ごめんなさい": {"level": 5, "meaning": "sorry, excuse me"},
    "さようなら": {"level": 5, "meaning": "goodbye"},
    "いただきます": {"level": 5, "meaning": "said before eating"},
    "ごちそうさま": {"level": 5, "meaning": "thank you for the meal"},
    "お休み": {"level": 5, "meaning": "good night"},
}
JLPT_READING_OVERRIDES = {
    "いう": "言う",
    "いく": "行く",
    "ゆく": "行く",
    "みる": "見る",
    "くる": "来る",
    "よい": "良い",
    "いい": "良い",
}


class JLPTWords:
    def __init__(self, entries: Iterable[WordEntry]) -> None:
        self.entries = list(entries)
        self.by_surface: dict[str, WordEntry] = {}
        self.by_level: dict[int, list[WordEntry]] = {level: [] for level in range(1, 6)}
        for entry in self.entries:
            existing = self.by_surface.get(entry.surface)
            if existing is None or entry.level > existing.level:
                self.by_surface[entry.surface] = entry
            self.by_level.setdefault(entry.level, []).append(entry)
        self.by_reading = self._build_reading_index()

    def lookup(self, *surfaces: str | None) -> WordEntry | None:
        for surface in surfaces:
            if surface and surface in self.by_surface:
                return self.by_surface[surface]
        return None

    def lookup_reading(self, *readings: str | None) -> WordEntry | None:
        for reading in readings:
            if not reading:
                continue
            override_surface = JLPT_READING_OVERRIDES.get(reading)
            if override_surface and override_surface in self.by_surface:
                return self.by_surface[override_surface]
            if reading in self.by_reading:
                return self.by_reading[reading]
        return None

    def total_by_level(self, level: int) -> int:
        return len({entry.surface for entry in self.by_level.get(level, [])})

    def _build_reading_index(self) -> dict[str, WordEntry]:
        entries_by_reading: dict[str, list[WordEntry]] = {}
        for entry in self.by_surface.values():
            for reading in split_readings(entry.reading):
                entries_by_reading.setdefault(reading, []).append(entry)
        return {
            reading: entries[0]
            for reading, entries in entries_by_reading.items()
            if len({entry.surface for entry in entries}) == 1
        }


def load_jlpt_words(path: Path) -> JLPTWords:
    if not path.exists():
        raise FileNotFoundError(
            f"JLPT word list not found: {path}. Use Full refresh in the viewer or place a real list there."
        )
    if path.suffix.casefold() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return JLPTWords(_entries_with_overrides(_entry_from_mapping(row) for row in csv.DictReader(handle)))
    payload = json.loads(path.read_text(encoding="utf-8"))
    return JLPTWords(_entries_with_overrides(_entries_from_json(payload)))


def _entries_with_overrides(entries: Iterable[WordEntry]) -> Iterable[WordEntry]:
    seen: set[str] = set()
    for entry in entries:
        seen.add(entry.surface)
        yield entry
    for surface, override in JLPT_ENTRY_OVERRIDES.items():
        if surface in seen:
            continue
        yield WordEntry(
            surface=surface,
            reading=str(override.get("reading") or surface),
            level=int(override.get("level", 5)),
            meaning=str(override.get("meaning") or ""),
        )


def _entries_from_json(payload: Any) -> Iterable[WordEntry]:
    if isinstance(payload, dict) and "words" in payload:
        payload = payload["words"]
    if isinstance(payload, dict):
        for level_key, words in payload.items():
            level = parse_level(level_key)
            if level is None:
                continue
            for item in words:
                if isinstance(item, str):
                    yield WordEntry(surface=item, reading=None, level=level)
                elif isinstance(item, dict):
                    yield _entry_from_mapping(item, default_level=level)
        return
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                yield _entry_from_mapping(item)


def _entry_from_mapping(mapping: dict[str, Any], default_level: int | None = None) -> WordEntry:
    surface = _first(mapping, WORD_KEYS)
    if not surface:
        raise ValueError(f"JLPT word row has no word field: {mapping!r}")
    level = parse_level(_first(mapping, LEVEL_KEYS)) or parse_level(_first(mapping, TAG_KEYS)) or default_level
    if level is None:
        raise ValueError(f"JLPT word row has no level field: {mapping!r}")
    surface_text = normalize_jlpt_pattern(str(surface))
    reading = normalize_jlpt_reading(_string_or_none(_first(mapping, READING_KEYS)))
    meaning = _string_or_none(_first(mapping, MEANING_KEYS))
    override = JLPT_ENTRY_OVERRIDES.get(surface_text)
    if override:
        level = int(override.get("level", level))
        reading = str(override.get("reading") or reading or "")
        meaning = str(override.get("meaning") or meaning or "")
    return WordEntry(
        surface=surface_text,
        reading=reading,
        level=level,
        meaning=meaning,
    )


def _first(mapping: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
    return None


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_jlpt_pattern(value: str) -> str:
    text = normalize_jlpt_text(value)
    text = re.sub(r"\s*[（(][^）)]*[～〜][^）)]*[）)]\s*$", "", text)
    text = re.sub(r"\s*[（(][ぁ-ゖァ-ヺー・/／;；\s]+[）)]\s*$", "", text)
    text = text.strip("～〜 　")
    return text or value.strip()


def normalize_jlpt_reading(value: str | None) -> str | None:
    if not value:
        return value
    text = normalize_jlpt_text(value)
    text = re.sub(r"\s*[（(][^）)]*[～〜][^）)]*[）)]\s*$", "", text)
    text = re.sub(r"\s*[（(][ぁ-ゖァ-ヺー・/／;；\s]+[）)]\s*$", "", text)
    text = text.strip("～〜 　")
    return text or value.strip()


def normalize_jlpt_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("〜", "～")).strip()


def parse_level(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int) and 1 <= value <= 5:
        return value
    text = str(value).upper().strip()
    match = re.search(r"(?:JLPT[_\s-]?|N)([1-5])\b", text)
    if match:
        return int(match.group(1))
    if text.startswith("N"):
        text = text[1:]
    try:
        number = int(text)
    except ValueError:
        return None
    if 1 <= number <= 5:
        return number
    return None


def split_readings(value: str | None) -> list[str]:
    if not value:
        return []
    return [
        part.strip()
        for part in str(value).replace("；", ";").replace("、", ";").replace(",", ";").split(";")
        if part.strip()
    ]


def download_jlpt_words(
    path: Path,
    *,
    source_url: str = "https://raw.githubusercontent.com/elzup/jlpt-word-list/master/out/all.csv",
    timeout: float = 60.0,
) -> Path:
    ensure_parent(path)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.get(source_url)
        response.raise_for_status()
    rows = list(csv.DictReader(response.text.splitlines()))
    entries = [_entry_from_mapping(row) for row in rows if any(row.values())]
    payload = [
        {
            "word": entry.surface,
            "reading": entry.reading,
            "level": entry.level_label,
            "meaning": entry.meaning,
        }
        for entry in entries
    ]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def write_sample_jlpt(path: Path) -> Path:
    ensure_parent(path)
    sample = [
        {"word": "私", "reading": "わたし", "level": "N5", "meaning": "I; me"},
        {"word": "見る", "reading": "みる", "level": "N5", "meaning": "to see; to watch"},
        {"word": "行く", "reading": "いく", "level": "N5", "meaning": "to go"},
        {"word": "出る", "reading": "でる", "level": "N5", "meaning": "to leave; to appear"},
        {"word": "気持ち", "reading": "きもち", "level": "N4", "meaning": "feeling"},
        {"word": "約束", "reading": "やくそく", "level": "N4", "meaning": "promise"},
        {"word": "微妙", "reading": "びみょう", "level": "N3", "meaning": "subtle; delicate"},
        {"word": "生意気", "reading": "なまいき", "level": "N2", "meaning": "impertinent"},
        {"word": "曖昧", "reading": "あいまい", "level": "N2", "meaning": "ambiguous"},
        {"word": "矛盾", "reading": "むじゅん", "level": "N1", "meaning": "contradiction"},
    ]
    path.write_text(json.dumps(sample, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
