from __future__ import annotations

import hashlib
import json
import re
import time
import unicodedata
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import httpx

from .models import LyricFile, MusicTrack, SubtitleLine
from .paths import ensure_dir
from .subtitle import contains_japanese, read_text


LRCLIB_BASE = "https://lrclib.net"
LRCLIB_CACHE_PURPOSE = "lrclib-match"
LRCLIB_CACHE_VERSION = 4
LRCLIB_ALBUM_CACHE_PURPOSE = "lrclib-album-search"
LRCLIB_ALBUM_CACHE_VERSION = 1
MIN_LRCLIB_SCORE = 10.0
SHORT_TITLE_MAX_LENGTH = 3
LRC_TIME_RE = re.compile(r"\[(?P<minute>\d{1,3}):(?P<second>\d{2})(?:[.:](?P<fraction>\d{1,3}))?\]")
INSTRUMENTAL_TITLE_RE = re.compile(
    r"(\binstrumental\b|\binst\.?\b|off\s*vocal|karaoke|カラオケ|オフボーカル)",
    re.IGNORECASE,
)
KANA_RE = re.compile(r"[\u3040-\u30ff]")
ARTIST_SPLIT_RE = re.compile(r"\s*(?:、|,|/|／|;|；|&|＆| feat\.? | ft\.? )\s*", re.IGNORECASE)


class LrcLibClient:
    def __init__(
        self,
        *,
        user_agent: str,
        timeout: float = 30.0,
        retries: int = 2,
    ) -> None:
        self.user_agent = user_agent
        self.timeout = timeout
        self.retries = retries

    def search(
        self,
        *,
        q: str | None = None,
        track_name: str | None = None,
        artist_name: str | None = None,
        album_name: str | None = None,
        duration_ms: int | None = None,
    ) -> list[dict[str, Any]]:
        if not q and not track_name:
            raise ValueError("LRCLIB search needs either q or track_name.")
        params: dict[str, Any] = {}
        if q:
            params["q"] = q
        if track_name:
            params["track_name"] = track_name
        if artist_name:
            params["artist_name"] = artist_name
        if album_name:
            params["album_name"] = album_name
        if duration_ms is not None:
            params["duration"] = round(duration_ms / 1000)
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            for attempt in range(self.retries + 1):
                response = client.get(
                    f"{LRCLIB_BASE}/api/search",
                    headers={"User-Agent": self.user_agent},
                    params=params,
                )
                if response.status_code not in {429, 500, 502, 503, 504} or attempt >= self.retries:
                    response.raise_for_status()
                    payload = response.json()
                    break
                time.sleep(0.5 * (attempt + 1))
        if not isinstance(payload, list):
            return []
        return [item for item in payload if isinstance(item, dict)]

    def best_match(
        self,
        track: MusicTrack,
        *,
        extra_results: Iterable[dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        if is_probably_instrumental_title(track.title):
            return None
        candidates: dict[str, dict[str, Any]] = {}
        for result in extra_results or []:
            source_id = str(result.get("id") or result.get("trackId") or repr(result))
            candidates[source_id] = result
        for params in lyric_search_params(track):
            for result in self.search(**params):
                source_id = str(result.get("id") or result.get("trackId") or repr(result))
                candidates[source_id] = result
        scored = [
            (score_lrclib_result(track, result), result)
            for result in candidates.values()
            if lyric_text(result) and not result.get("instrumental")
        ]
        scored = [(score, result) for score, result in scored if score >= MIN_LRCLIB_SCORE]
        if not scored:
            return None
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[0][1]


def lyric_search_params(track: MusicTrack) -> list[dict[str, Any]]:
    titles = [track.title]
    if track.title_zh and contains_japanese(track.title_zh):
        titles.append(track.title_zh)
    seen_titles = []
    for title in titles:
        title = title.strip()
        if title and title not in seen_titles:
            seen_titles.append(title)

    params = []
    for title in seen_titles:
        base = {
            "track_name": title,
            "duration_ms": track.duration_ms,
        }
        for artist in artist_candidates(track):
            params.append({**base, "artist_name": artist, "album_name": track.album_title})
            params.append({**base, "artist_name": artist})
        params.append({**base, "album_name": track.album_title})
        params.append(base)
    deduped = []
    seen = set()
    for item in params:
        key = tuple(sorted((name, value) for name, value in item.items() if value))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def lyric_album_search_params(album_title: str, artists: Iterable[str] = ()) -> list[dict[str, Any]]:
    album_title = album_title.strip()
    if not album_title:
        return []
    params: list[dict[str, Any]] = []
    for artist in artists:
        artist = artist.strip()
        if artist:
            params.append({"q": album_title, "album_name": album_title, "artist_name": artist})
    params.append({"q": album_title, "album_name": album_title})
    params.append({"q": album_title})
    deduped = []
    seen = set()
    for item in params:
        key = tuple(sorted((name, value) for name, value in item.items() if value))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def lyric_album_artists(tracks: Iterable[MusicTrack]) -> list[str]:
    candidates = []
    for track in tracks:
        for artist in artist_candidates(track):
            if artist not in candidates:
                candidates.append(artist)
    return candidates[:16]


def is_probably_instrumental_title(value: str) -> bool:
    return bool(INSTRUMENTAL_TITLE_RE.search(value))


def score_lrclib_result(track: MusicTrack, result: dict[str, Any]) -> float:
    text = lyric_text(result)
    if not text or not contains_kana(text):
        return 0.0
    result_title_raw = str(result.get("trackName") or "")
    if is_probably_instrumental_title(result_title_raw) and not is_probably_instrumental_title(track.title):
        return 0.0
    title_score, title_match = title_match_score(track.title, result_title_raw)
    if title_score == 0.0:
        return 0.0
    artist_match = result_artist_matches(track, result)
    album_match = result_album_matches(track, result)
    if is_short_match_title(track.title) and not (artist_match or album_match):
        return 0.0

    score = 1.0
    if result.get("syncedLyrics"):
        score += 5.0
    if result.get("plainLyrics"):
        score += 2.0
    score += title_score
    if artist_match:
        score += 5.0
    if album_match:
        score += 3.0
    if track.duration_ms and result.get("duration"):
        delta = abs(round(track.duration_ms / 1000) - int(float(result["duration"])))
        score += max(0.0, 2.0 - delta / 8.0)
    return score


def title_match_score(track_title: str, result_title: str) -> tuple[float, str]:
    track_key = normalize_match_text(track_title)
    result_key = normalize_match_text(result_title)
    if not track_key or not result_key:
        return 0.0, "none"
    if track_key == result_key:
        return 8.0, "exact"
    if track_key in result_key or result_key in track_key:
        return 3.0, "partial"
    return 0.0, "none"


def artist_candidates(track: MusicTrack) -> list[str]:
    if not track.artist:
        return []
    candidates = []
    for value in ARTIST_SPLIT_RE.split(track.artist):
        value = value.strip()
        if value and value not in candidates:
            candidates.append(value)
    if track.artist not in candidates:
        candidates.append(track.artist)
    return candidates[:12]


def result_artist_matches(track: MusicTrack, result: dict[str, Any]) -> bool:
    result_artist = normalize_match_text(str(result.get("artistName") or ""))
    if not result_artist:
        return False
    for artist in artist_candidates(track):
        artist_key = normalize_match_text(artist)
        if artist_key and (artist_key == result_artist or artist_key in result_artist or result_artist in artist_key):
            return True
    return False


def result_album_matches(track: MusicTrack, result: dict[str, Any]) -> bool:
    track_album = normalize_match_text(track.album_title)
    result_album = normalize_match_text(str(result.get("albumName") or ""))
    return bool(track_album and result_album and (track_album == result_album or track_album in result_album or result_album in track_album))


def is_short_match_title(value: str) -> bool:
    return len(normalize_match_text(value)) <= SHORT_TITLE_MAX_LENGTH


def contains_kana(text: str) -> bool:
    return bool(KANA_RE.search(text))


def write_lrclib_lyric(
    track: MusicTrack,
    result: dict[str, Any],
    *,
    cache_dir: Path,
) -> LyricFile:
    text = lyric_text(result)
    if not text:
        raise ValueError(f"LRCLIB result has no lyrics for {track.title}.")
    ensure_dir(cache_dir)
    source_id = str(result.get("id") or result.get("trackId") or "unknown")
    synced = bool(result.get("syncedLyrics"))
    suffix = "lrc" if synced else "txt"
    filename = f"{safe_filename(track.track_key)}-{safe_filename(source_id)}.{suffix}"
    path = cache_dir / filename
    path.write_text(text.strip() + "\n", encoding="utf-8")
    return LyricFile(
        track_key=track.track_key,
        bangumi_id=track.bangumi_id,
        track_title=track.title,
        album_title=track.album_title,
        artist=track.artist,
        path=path,
        provider="lrclib",
        source_id=source_id,
        source_url=f"{LRCLIB_BASE}/api/get/{source_id}",
        synced=synced,
    )


def parse_lyrics(path: Path) -> list[SubtitleLine]:
    suffix = path.suffix.casefold()
    text = read_text(path)
    if suffix == ".lrc":
        return parse_lrc_text(text)
    return [
        SubtitleLine(line.strip())
        for line in text.splitlines()
        if line.strip() and contains_japanese(line)
    ]


def parse_lrc_text(text: str) -> list[SubtitleLine]:
    timed_lines: list[tuple[int, str]] = []
    for raw_line in text.splitlines():
        matches = list(LRC_TIME_RE.finditer(raw_line))
        if not matches:
            continue
        body = raw_line[matches[-1].end() :].strip()
        if not body or not contains_japanese(body):
            continue
        for match in matches:
            timed_lines.append((lrc_timestamp_to_ms(match), body))
    timed_lines.sort(key=lambda item: item[0])
    lines = []
    for index, (start_ms, body) in enumerate(timed_lines):
        end_ms = timed_lines[index + 1][0] if index + 1 < len(timed_lines) else None
        lines.append(SubtitleLine(text=body, start_ms=start_ms, end_ms=end_ms))
    return lines


def lrc_timestamp_to_ms(match: re.Match[str]) -> int:
    fraction = (match.group("fraction") or "0").ljust(3, "0")[:3]
    return int(match.group("minute")) * 60_000 + int(match.group("second")) * 1000 + int(fraction)


def lyric_text(result: dict[str, Any]) -> str:
    return str(result.get("syncedLyrics") or result.get("plainLyrics") or "").strip()


def lyric_cache_key(track: MusicTrack) -> str:
    payload = {
        "title": normalize_cache_text(track.title),
        "title_zh": normalize_cache_text(track.title_zh or ""),
        "artist": [normalize_cache_text(value) for value in artist_candidates(track)],
        "album": normalize_cache_text(track.album_title),
        "duration_ms": track.duration_ms,
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def lyric_album_cache_key(album_title: str, artists: Iterable[str] = ()) -> str:
    payload = {
        "album": normalize_cache_text(album_title),
        "artists": [normalize_cache_text(artist) for artist in artists],
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def normalize_match_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[\s\W_]+", "", value, flags=re.UNICODE)


def normalize_cache_text(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value).casefold()).strip()


def safe_filename(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r"[^0-9A-Za-z._-]+", "_", value).strip("._")
    return value or "lyrics"
