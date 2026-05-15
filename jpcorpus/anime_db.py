from __future__ import annotations

import json
import re
import string
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import httpx

from .models import ExternalIds, WatchedShow
from .paths import ensure_parent


SOURCE_PATTERNS = {
    "mal_id": re.compile(r"myanimelist\.net/anime/(\d+)"),
    "anilist_id": re.compile(r"anilist\.co/anime/(\d+)"),
    "anidb_id": re.compile(r"anidb\.net/anime/(\d+)"),
    "bangumi_id": re.compile(r"(?:bgm\.tv|bangumi\.tv)/subject/(\d+)"),
}

PUNCTUATION = string.punctuation + "　・「」『』（）()[]【】〈〉《》、。！？!?,.:;:-_~〜"


@dataclass(frozen=True)
class AnimeRecord:
    title: str
    synonyms: tuple[str, ...]
    year: int | None
    episodes: int | None
    ids: ExternalIds


def normalize_title(title: str) -> str:
    normalized = unicodedata.normalize("NFKC", title).casefold()
    return "".join(ch for ch in normalized if ch not in PUNCTUATION and not ch.isspace())


def _first_source_id(sources: Iterable[str], key: str) -> int | None:
    pattern = SOURCE_PATTERNS[key]
    for source in sources:
        match = pattern.search(source)
        if match:
            return int(match.group(1))
    return None


def _record_from_item(item: dict[str, Any]) -> AnimeRecord:
    sources = item.get("sources") or []
    season = item.get("animeSeason") or {}
    return AnimeRecord(
        title=item.get("title") or "",
        synonyms=tuple(item.get("synonyms") or ()),
        year=season.get("year"),
        episodes=item.get("episodes"),
        ids=ExternalIds(
            mal_id=_first_source_id(sources, "mal_id"),
            anilist_id=_first_source_id(sources, "anilist_id"),
            anidb_id=_first_source_id(sources, "anidb_id"),
            bangumi_id=_first_source_id(sources, "bangumi_id"),
        ),
    )


class AnimeOfflineIndex:
    def __init__(self, records: Iterable[AnimeRecord]) -> None:
        self.records = list(records)
        self.by_bangumi: dict[int, AnimeRecord] = {}
        self.by_title_year: dict[tuple[str, int | None], list[AnimeRecord]] = {}
        for record in self.records:
            if record.ids.bangumi_id is not None:
                self.by_bangumi[record.ids.bangumi_id] = record
            for title in (record.title, *record.synonyms):
                key = normalize_title(title)
                if not key:
                    continue
                self.by_title_year.setdefault((key, record.year), []).append(record)
                self.by_title_year.setdefault((key, None), []).append(record)

    @classmethod
    def load(cls, path: Path) -> "AnimeOfflineIndex":
        if not path.exists():
            raise FileNotFoundError(
                f"Anime Offline Database not found: {path}. Use Full refresh in the viewer first."
            )
        if path.suffix == ".jsonl":
            records = []
            with path.open("r", encoding="utf-8") as handle:
                for line_number, line in enumerate(handle):
                    payload = json.loads(line)
                    if line_number == 0 and "data" not in payload and "sources" not in payload:
                        continue
                    if "sources" in payload:
                        records.append(_record_from_item(payload))
            return cls(records)
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(_record_from_item(item) for item in payload.get("data", []))

    def match_show(self, show: WatchedShow) -> AnimeRecord | None:
        direct = self.by_bangumi.get(show.bangumi_id)
        if direct:
            return direct

        titles = [show.title_jp]
        if show.title_zh:
            titles.append(show.title_zh)
        for title in titles:
            normalized = normalize_title(title)
            if not normalized:
                continue
            candidates = self.by_title_year.get((normalized, show.year), [])
            if not candidates:
                candidates = self.by_title_year.get((normalized, None), [])
            chosen = self._choose_candidate(candidates, show)
            if chosen:
                return chosen
        return None

    def _choose_candidate(self, candidates: list[AnimeRecord], show: WatchedShow) -> AnimeRecord | None:
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]
        bangumi_eps = show.subject.get("eps") or show.subject.get("total_episodes")
        if isinstance(bangumi_eps, int):
            for candidate in candidates:
                if candidate.episodes == bangumi_eps:
                    return candidate
        return candidates[0]


def download_latest_anime_db(target: Path, *, timeout: float = 120.0) -> Path:
    ensure_parent(target)
    api_url = "https://api.github.com/repos/manami-project/anime-offline-database/releases/latest"
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        release = client.get(api_url)
        release.raise_for_status()
        assets = release.json().get("assets", [])
        asset = next(
            (
                item
                for item in assets
                if item.get("name") == "anime-offline-database-minified.json"
            ),
            None,
        )
        if asset is None:
            asset = next(
                (
                    item
                    for item in assets
                    if item.get("name") == "anime-offline-database.json"
                ),
                None,
            )
        if asset is None:
            raise RuntimeError("Latest release has no JSON anime database asset.")
        response = client.get(asset["browser_download_url"])
        response.raise_for_status()
        target.write_bytes(response.content)
    return target
