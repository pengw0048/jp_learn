from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

import httpx

from .models import LyricFile, MusicTrack, SubtitleLine
from .paths import ensure_dir
from .subtitle import contains_japanese, read_text


LRCLIB_BASE = "https://lrclib.net"
LRC_TIME_RE = re.compile(r"\[(?P<minute>\d{1,3}):(?P<second>\d{2})(?:[.:](?P<fraction>\d{1,3}))?\]")
INSTRUMENTAL_TITLE_RE = re.compile(
    r"(\binstrumental\b|\binst\.?\b|off\s*vocal|karaoke|カラオケ|オフボーカル)",
    re.IGNORECASE,
)


class LrcLibClient:
    def __init__(
        self,
        *,
        user_agent: str,
        timeout: float = 30.0,
    ) -> None:
        self.user_agent = user_agent
        self.timeout = timeout

    def search(
        self,
        *,
        track_name: str,
        artist_name: str | None = None,
        album_name: str | None = None,
        duration_ms: int | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"track_name": track_name}
        if artist_name:
            params["artist_name"] = artist_name
        if album_name:
            params["album_name"] = album_name
        if duration_ms is not None:
            params["duration"] = round(duration_ms / 1000)
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            response = client.get(
                f"{LRCLIB_BASE}/api/search",
                headers={"User-Agent": self.user_agent},
                params=params,
            )
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, list):
            return []
        return [item for item in payload if isinstance(item, dict)]

    def best_match(self, track: MusicTrack) -> dict[str, Any] | None:
        if is_probably_instrumental_title(track.title):
            return None
        candidates: dict[str, dict[str, Any]] = {}
        for params in lyric_search_params(track):
            for result in self.search(**params):
                source_id = str(result.get("id") or result.get("trackId") or repr(result))
                candidates[source_id] = result
        scored = [
            (score_lrclib_result(track, result), result)
            for result in candidates.values()
            if lyric_text(result) and not result.get("instrumental")
        ]
        scored = [(score, result) for score, result in scored if score > 0]
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
        if track.artist:
            params.append({**base, "artist_name": track.artist, "album_name": track.album_title})
            params.append({**base, "artist_name": track.artist})
        params.append({**base, "album_name": track.album_title})
        params.append(base)
    return params


def is_probably_instrumental_title(value: str) -> bool:
    return bool(INSTRUMENTAL_TITLE_RE.search(value))


def score_lrclib_result(track: MusicTrack, result: dict[str, Any]) -> float:
    text = lyric_text(result)
    if not text or not contains_japanese(text):
        return 0.0
    score = 1.0
    if result.get("syncedLyrics"):
        score += 5.0
    if result.get("plainLyrics"):
        score += 2.0
    track_title = normalize_match_text(track.title)
    result_title = normalize_match_text(str(result.get("trackName") or ""))
    if track_title and result_title:
        if track_title == result_title:
            score += 8.0
        elif track_title in result_title or result_title in track_title:
            score += 3.0
    if track.artist:
        track_artist = normalize_match_text(track.artist)
        result_artist = normalize_match_text(str(result.get("artistName") or ""))
        if track_artist and result_artist:
            if track_artist == result_artist:
                score += 3.0
            elif track_artist in result_artist or result_artist in track_artist:
                score += 1.0
    if track.duration_ms and result.get("duration"):
        delta = abs(round(track.duration_ms / 1000) - int(float(result["duration"])))
        score += max(0.0, 2.0 - delta / 8.0)
    return score


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


def normalize_match_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[\s\W_]+", "", value, flags=re.UNICODE)


def safe_filename(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r"[^0-9A-Za-z._-]+", "_", value).strip("._")
    return value or "lyrics"
