from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

from .models import WordEntry
from .paths import ensure_parent


WORD_KEYS = ("word", "surface", "kanji", "expression", "term", "vocab", "text")
READING_KEYS = ("reading", "kana", "furigana", "pronunciation")
LEVEL_KEYS = ("level", "jlpt", "jlpt_level")
MEANING_KEYS = ("meaning", "translation", "gloss", "english", "zh")


class JLPTWords:
    def __init__(self, entries: Iterable[WordEntry]) -> None:
        self.entries = list(entries)
        self.by_surface: dict[str, WordEntry] = {}
        self.by_level: dict[int, list[WordEntry]] = {level: [] for level in range(1, 6)}
        for entry in self.entries:
            existing = self.by_surface.get(entry.surface)
            if existing is None or entry.level < existing.level:
                self.by_surface[entry.surface] = entry
            self.by_level.setdefault(entry.level, []).append(entry)

    def lookup(self, *surfaces: str | None) -> WordEntry | None:
        for surface in surfaces:
            if surface and surface in self.by_surface:
                return self.by_surface[surface]
        return None

    def total_by_level(self, level: int) -> int:
        return len({entry.surface for entry in self.by_level.get(level, [])})


def load_jlpt_words(path: Path) -> JLPTWords:
    if not path.exists():
        raise FileNotFoundError(
            f"JLPT word list not found: {path}. Run `jpcorpus data init-sample-jlpt` or place a real list there."
        )
    if path.suffix.casefold() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return JLPTWords(_entry_from_mapping(row) for row in csv.DictReader(handle))
    payload = json.loads(path.read_text(encoding="utf-8"))
    return JLPTWords(_entries_from_json(payload))


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
    level = parse_level(_first(mapping, LEVEL_KEYS)) or default_level
    if level is None:
        raise ValueError(f"JLPT word row has no level field: {mapping!r}")
    return WordEntry(
        surface=str(surface),
        reading=_string_or_none(_first(mapping, READING_KEYS)),
        level=level,
        meaning=_string_or_none(_first(mapping, MEANING_KEYS)),
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


def parse_level(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int) and 1 <= value <= 5:
        return value
    text = str(value).upper().strip()
    if text.startswith("N"):
        text = text[1:]
    try:
        number = int(text)
    except ValueError:
        return None
    if 1 <= number <= 5:
        return number
    return None


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

