from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class WatchedShow:
    bangumi_id: int
    title_jp: str
    title_zh: str | None = None
    air_date: str | None = None
    year: int | None = None
    ep_status: int | None = None
    subject: dict[str, Any] = field(default_factory=dict)
    collection: dict[str, Any] = field(default_factory=dict)
    mal_id: int | None = None
    anilist_id: int | None = None
    anidb_id: int | None = None
    jimaku_entry_id: int | None = None

    @property
    def display_title(self) -> str:
        return self.title_zh or self.title_jp or f"Bangumi {self.bangumi_id}"


@dataclass(frozen=True)
class ExternalIds:
    mal_id: int | None = None
    anilist_id: int | None = None
    anidb_id: int | None = None
    bangumi_id: int | None = None


@dataclass(frozen=True)
class SubtitleFile:
    bangumi_id: int
    show_title: str
    path: Path
    name: str
    episode: int | None = None
    url: str | None = None
    show_summary: str | None = None
    show_characters: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SubtitleLine:
    text: str
    start_ms: int | None = None
    end_ms: int | None = None


@dataclass(frozen=True)
class Token:
    surface: str
    base: str
    reading: str | None = None
    pos: str | None = None


@dataclass(frozen=True)
class WordEntry:
    surface: str
    reading: str | None
    level: int
    meaning: str | None = None
    meaning_zh: str | None = None

    @property
    def level_label(self) -> str:
        return f"N{self.level}"
