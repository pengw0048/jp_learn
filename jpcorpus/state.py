from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import LyricFile, MusicTrack, SubtitleFile, WatchedShow
from .paths import DEFAULT_STATE_DB, ensure_parent


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class State:
    def __init__(self, path: Path = DEFAULT_STATE_DB) -> None:
        self.path = path
        ensure_parent(path)
        self._init_db()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS oauth_tokens (
                  service TEXT PRIMARY KEY,
                  access_token TEXT NOT NULL,
                  refresh_token TEXT,
                  expires_at INTEGER,
                  user_id TEXT,
                  username TEXT,
                  raw_json TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS watched_shows (
                  bangumi_id INTEGER PRIMARY KEY,
                  title_jp TEXT NOT NULL,
                  title_zh TEXT,
                  air_date TEXT,
                  year INTEGER,
                  ep_status INTEGER,
                  subject_json TEXT NOT NULL,
                  collection_json TEXT NOT NULL,
                  mal_id INTEGER,
                  anilist_id INTEGER,
                  anidb_id INTEGER,
                  jimaku_entry_id INTEGER,
                  updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS watched_shows_anilist_idx
                  ON watched_shows(anilist_id);

                CREATE TABLE IF NOT EXISTS show_characters (
                  bangumi_id INTEGER NOT NULL,
                  character_id INTEGER NOT NULL,
                  name TEXT NOT NULL,
                  relation TEXT,
                  raw_json TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  PRIMARY KEY (bangumi_id, character_id),
                  FOREIGN KEY (bangumi_id) REFERENCES watched_shows(bangumi_id)
                );

                CREATE INDEX IF NOT EXISTS show_characters_bangumi_idx
                  ON show_characters(bangumi_id);

                CREATE TABLE IF NOT EXISTS subtitle_files (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  bangumi_id INTEGER NOT NULL,
                  jimaku_entry_id INTEGER,
                  episode INTEGER,
                  name TEXT NOT NULL,
                  url TEXT UNIQUE,
                  size INTEGER,
                  local_path TEXT NOT NULL UNIQUE,
                  downloaded_at TEXT NOT NULL,
                  FOREIGN KEY (bangumi_id) REFERENCES watched_shows(bangumi_id)
                );

                CREATE TABLE IF NOT EXISTS music_tracks (
                  track_key TEXT PRIMARY KEY,
                  bangumi_id INTEGER NOT NULL,
                  bangumi_episode_id INTEGER,
                  title TEXT NOT NULL,
                  title_zh TEXT,
                  album_title TEXT NOT NULL,
                  artist TEXT,
                  track_number INTEGER,
                  disc INTEGER,
                  duration_ms INTEGER,
                  subject_json TEXT NOT NULL,
                  episode_json TEXT NOT NULL,
                  collection_json TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS music_tracks_bangumi_idx
                  ON music_tracks(bangumi_id);

                CREATE TABLE IF NOT EXISTS lyric_files (
                  track_key TEXT NOT NULL,
                  provider TEXT NOT NULL,
                  source_id TEXT,
                  source_url TEXT,
                  track_title TEXT NOT NULL,
                  album_title TEXT NOT NULL,
                  artist TEXT,
                  synced INTEGER NOT NULL DEFAULT 0,
                  local_path TEXT NOT NULL UNIQUE,
                  raw_json TEXT NOT NULL,
                  fetched_at TEXT NOT NULL,
                  PRIMARY KEY (track_key, provider),
                  FOREIGN KEY (track_key) REFERENCES music_tracks(track_key)
                );

                CREATE TABLE IF NOT EXISTS lyric_misses (
                  track_key TEXT NOT NULL,
                  provider TEXT NOT NULL,
                  reason TEXT NOT NULL,
                  detail TEXT,
                  missed_at TEXT NOT NULL,
                  PRIMARY KEY (track_key, provider),
                  FOREIGN KEY (track_key) REFERENCES music_tracks(track_key)
                );

                CREATE TABLE IF NOT EXISTS cache_entries (
                  purpose TEXT NOT NULL,
                  cache_key TEXT NOT NULL,
                  version INTEGER NOT NULL,
                  status TEXT NOT NULL,
                  value_json TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  PRIMARY KEY (purpose, cache_key, version)
                );
                """
            )

    def save_token(
        self,
        service: str,
        payload: dict[str, Any],
        *,
        user_id: str | int | None = None,
        username: str | None = None,
        expires_at: int | None = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO oauth_tokens
                  (service, access_token, refresh_token, expires_at, user_id, username, raw_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(service) DO UPDATE SET
                  access_token=excluded.access_token,
                  refresh_token=excluded.refresh_token,
                  expires_at=excluded.expires_at,
                  user_id=excluded.user_id,
                  username=excluded.username,
                  raw_json=excluded.raw_json,
                  updated_at=excluded.updated_at
                """,
                (
                    service,
                    payload["access_token"],
                    payload.get("refresh_token"),
                    expires_at,
                    str(user_id) if user_id is not None else None,
                    username,
                    json.dumps(payload, ensure_ascii=False),
                    utc_now(),
                ),
            )

    def get_token(self, service: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM oauth_tokens WHERE service = ?",
                (service,),
            ).fetchone()
        if row is None:
            return None
        payload = json.loads(row["raw_json"])
        payload.update(
            {
                "access_token": row["access_token"],
                "refresh_token": row["refresh_token"],
                "expires_at": row["expires_at"],
                "user_id": row["user_id"],
                "username": row["username"],
            }
        )
        return payload

    def save_watched_show(self, show: WatchedShow) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO watched_shows
                  (bangumi_id, title_jp, title_zh, air_date, year, ep_status,
                   subject_json, collection_json, mal_id, anilist_id, anidb_id,
                   jimaku_entry_id, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(bangumi_id) DO UPDATE SET
                  title_jp=excluded.title_jp,
                  title_zh=excluded.title_zh,
                  air_date=excluded.air_date,
                  year=excluded.year,
                  ep_status=excluded.ep_status,
                  subject_json=excluded.subject_json,
                  collection_json=excluded.collection_json,
                  mal_id=COALESCE(excluded.mal_id, watched_shows.mal_id),
                  anilist_id=COALESCE(excluded.anilist_id, watched_shows.anilist_id),
                  anidb_id=COALESCE(excluded.anidb_id, watched_shows.anidb_id),
                  jimaku_entry_id=COALESCE(excluded.jimaku_entry_id, watched_shows.jimaku_entry_id),
                  updated_at=excluded.updated_at
                """,
                (
                    show.bangumi_id,
                    show.title_jp,
                    show.title_zh,
                    show.air_date,
                    show.year,
                    show.ep_status,
                    json.dumps(show.subject, ensure_ascii=False),
                    json.dumps(show.collection, ensure_ascii=False),
                    show.mal_id,
                    show.anilist_id,
                    show.anidb_id,
                    show.jimaku_entry_id,
                    utc_now(),
                ),
            )

    def save_show_characters(self, bangumi_id: int, characters: list[dict[str, Any]]) -> None:
        now = utc_now()
        with self.connect() as conn:
            conn.execute("DELETE FROM show_characters WHERE bangumi_id = ?", (bangumi_id,))
            conn.executemany(
                """
                INSERT INTO show_characters
                  (bangumi_id, character_id, name, relation, raw_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        bangumi_id,
                        int(character.get("id") or 0),
                        str(character.get("name") or "").strip(),
                        _string_or_none(character.get("relation")),
                        json.dumps(character, ensure_ascii=False),
                        now,
                    )
                    for character in characters
                    if character.get("id") and str(character.get("name") or "").strip()
                ],
            )

    def list_watched_shows(self, limit: int | None = None) -> list[WatchedShow]:
        sql = "SELECT * FROM watched_shows ORDER BY updated_at DESC, bangumi_id"
        params: tuple[Any, ...] = ()
        if limit is not None:
            sql += " LIMIT ?"
            params = (limit,)
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_show(row) for row in rows]

    def count_watched_shows(self) -> int:
        with self.connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM watched_shows").fetchone()[0])

    def update_external_ids(
        self,
        bangumi_id: int,
        *,
        mal_id: int | None = None,
        anilist_id: int | None = None,
        anidb_id: int | None = None,
        jimaku_entry_id: int | None = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE watched_shows
                SET mal_id = COALESCE(?, mal_id),
                    anilist_id = COALESCE(?, anilist_id),
                    anidb_id = COALESCE(?, anidb_id),
                    jimaku_entry_id = COALESCE(?, jimaku_entry_id),
                    updated_at = ?
                WHERE bangumi_id = ?
                """,
                (mal_id, anilist_id, anidb_id, jimaku_entry_id, utc_now(), bangumi_id),
            )

    def save_subtitle_file(
        self,
        *,
        bangumi_id: int,
        jimaku_entry_id: int | None,
        episode: int | None,
        name: str,
        url: str | None,
        size: int | None,
        local_path: Path,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO subtitle_files
                  (bangumi_id, jimaku_entry_id, episode, name, url, size, local_path, downloaded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(local_path) DO UPDATE SET
                  jimaku_entry_id=excluded.jimaku_entry_id,
                  episode=excluded.episode,
                  name=excluded.name,
                  url=excluded.url,
                  size=excluded.size,
                  downloaded_at=excluded.downloaded_at
                """,
                (
                    bangumi_id,
                    jimaku_entry_id,
                    episode,
                    name,
                    url,
                    size,
                    str(local_path),
                    utc_now(),
                ),
            )

    def list_subtitle_files(self) -> list[SubtitleFile]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT sf.*, ws.title_jp, ws.title_zh, ws.subject_json
                FROM subtitle_files sf
                JOIN watched_shows ws ON ws.bangumi_id = sf.bangumi_id
                ORDER BY ws.title_jp, sf.name
                """
            ).fetchall()
            character_rows = conn.execute(
                "SELECT bangumi_id, name FROM show_characters ORDER BY bangumi_id, name"
            ).fetchall()
        character_names_by_show: dict[int, list[str]] = {}
        for row in character_rows:
            character_names_by_show.setdefault(int(row["bangumi_id"]), []).append(row["name"])
        subtitle_files = []
        for row in rows:
            subject = json.loads(row["subject_json"])
            bangumi_id = int(row["bangumi_id"])
            subtitle_files.append(
                SubtitleFile(
                    bangumi_id=bangumi_id,
                    show_title=row["title_zh"] or row["title_jp"],
                    path=Path(row["local_path"]),
                    name=row["name"],
                    episode=row["episode"],
                    url=row["url"],
                    show_summary=clean_show_summary(subject),
                    show_characters=character_names_by_show.get(bangumi_id, []),
                )
            )
        return subtitle_files

    def save_music_track(self, track: MusicTrack) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO music_tracks
                  (track_key, bangumi_id, bangumi_episode_id, title, title_zh,
                   album_title, artist, track_number, disc, duration_ms,
                   subject_json, episode_json, collection_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(track_key) DO UPDATE SET
                  bangumi_id=excluded.bangumi_id,
                  bangumi_episode_id=excluded.bangumi_episode_id,
                  title=excluded.title,
                  title_zh=excluded.title_zh,
                  album_title=excluded.album_title,
                  artist=excluded.artist,
                  track_number=excluded.track_number,
                  disc=excluded.disc,
                  duration_ms=excluded.duration_ms,
                  subject_json=excluded.subject_json,
                  episode_json=excluded.episode_json,
                  collection_json=excluded.collection_json,
                  updated_at=excluded.updated_at
                """,
                (
                    track.track_key,
                    track.bangumi_id,
                    track.bangumi_episode_id,
                    track.title,
                    track.title_zh,
                    track.album_title,
                    track.artist,
                    track.track_number,
                    track.disc,
                    track.duration_ms,
                    json.dumps(track.subject, ensure_ascii=False),
                    json.dumps(track.episode, ensure_ascii=False),
                    json.dumps(track.collection, ensure_ascii=False),
                    utc_now(),
                ),
            )

    def list_music_tracks(self, limit: int | None = None) -> list[MusicTrack]:
        sql = """
            SELECT *
            FROM music_tracks
            ORDER BY album_title, COALESCE(disc, 1), COALESCE(track_number, 9999), title
        """
        params: tuple[Any, ...] = ()
        if limit is not None:
            sql += " LIMIT ?"
            params = (limit,)
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_music_track(row) for row in rows]

    def count_music_tracks(self) -> int:
        with self.connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM music_tracks").fetchone()[0])

    def save_lyric_file(
        self,
        lyric_file: LyricFile,
        *,
        raw_payload: dict[str, Any] | None = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO lyric_files
                  (track_key, provider, source_id, source_url, track_title,
                   album_title, artist, synced, local_path, raw_json, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(track_key, provider) DO UPDATE SET
                  source_id=excluded.source_id,
                  source_url=excluded.source_url,
                  track_title=excluded.track_title,
                  album_title=excluded.album_title,
                  artist=excluded.artist,
                  synced=excluded.synced,
                  local_path=excluded.local_path,
                  raw_json=excluded.raw_json,
                  fetched_at=excluded.fetched_at
                """,
                (
                    lyric_file.track_key,
                    lyric_file.provider,
                    lyric_file.source_id,
                    lyric_file.source_url,
                    lyric_file.track_title,
                    lyric_file.album_title,
                    lyric_file.artist,
                    1 if lyric_file.synced else 0,
                    str(lyric_file.path),
                    json.dumps(raw_payload or {}, ensure_ascii=False),
                    utc_now(),
                ),
            )
            conn.execute(
                "DELETE FROM lyric_misses WHERE track_key = ? AND provider = ?",
                (lyric_file.track_key, lyric_file.provider),
            )

    def list_lyric_files(self) -> list[LyricFile]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT lf.*, mt.bangumi_id
                FROM lyric_files lf
                JOIN music_tracks mt ON mt.track_key = lf.track_key
                ORDER BY lf.album_title, lf.track_title
                """
            ).fetchall()
        return [
            LyricFile(
                track_key=row["track_key"],
                bangumi_id=int(row["bangumi_id"]),
                track_title=row["track_title"],
                album_title=row["album_title"],
                artist=row["artist"],
                path=Path(row["local_path"]),
                provider=row["provider"],
                source_id=row["source_id"],
                source_url=row["source_url"],
                synced=bool(row["synced"]),
            )
            for row in rows
        ]

    def delete_lyric_file(self, *, track_key: str, provider: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "DELETE FROM lyric_files WHERE track_key = ? AND provider = ?",
                (track_key, provider),
            )

    def save_lyric_miss(
        self,
        *,
        track_key: str,
        provider: str,
        reason: str,
        detail: str | None = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO lyric_misses
                  (track_key, provider, reason, detail, missed_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(track_key, provider) DO UPDATE SET
                  reason=excluded.reason,
                  detail=excluded.detail,
                  missed_at=excluded.missed_at
                """,
                (track_key, provider, reason, detail, utc_now()),
            )

    def list_lyric_miss_keys(self, *, provider: str) -> set[str]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT track_key FROM lyric_misses WHERE provider = ?",
                (provider,),
            ).fetchall()
        return {row["track_key"] for row in rows}

    def count_lyric_misses(self, *, provider: str | None = None) -> int:
        sql = "SELECT COUNT(*) FROM lyric_misses"
        params: tuple[Any, ...] = ()
        if provider is not None:
            sql += " WHERE provider = ?"
            params = (provider,)
        with self.connect() as conn:
            return int(conn.execute(sql, params).fetchone()[0])

    def get_cache_entry(
        self,
        *,
        purpose: str,
        cache_key: str,
        version: int,
    ) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT status, value_json
                FROM cache_entries
                WHERE purpose = ? AND cache_key = ? AND version = ?
                """,
                (purpose, cache_key, version),
            ).fetchone()
        if row is None:
            return None
        return {
            "status": row["status"],
            "value": json.loads(row["value_json"]),
        }

    def save_cache_entry(
        self,
        *,
        purpose: str,
        cache_key: str,
        version: int,
        status: str,
        value: dict[str, Any] | list[Any] | str | int | float | bool | None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO cache_entries
                  (purpose, cache_key, version, status, value_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(purpose, cache_key, version) DO UPDATE SET
                  status=excluded.status,
                  value_json=excluded.value_json,
                  updated_at=excluded.updated_at
                """,
                (
                    purpose,
                    cache_key,
                    version,
                    status,
                    json.dumps(value, ensure_ascii=False),
                    utc_now(),
                ),
            )

    def _row_to_show(self, row: sqlite3.Row) -> WatchedShow:
        return WatchedShow(
            bangumi_id=int(row["bangumi_id"]),
            title_jp=row["title_jp"],
            title_zh=row["title_zh"],
            air_date=row["air_date"],
            year=row["year"],
            ep_status=row["ep_status"],
            subject=json.loads(row["subject_json"]),
            collection=json.loads(row["collection_json"]),
            mal_id=row["mal_id"],
            anilist_id=row["anilist_id"],
            anidb_id=row["anidb_id"],
            jimaku_entry_id=row["jimaku_entry_id"],
        )

    def _row_to_music_track(self, row: sqlite3.Row) -> MusicTrack:
        return MusicTrack(
            track_key=row["track_key"],
            bangumi_id=int(row["bangumi_id"]),
            bangumi_episode_id=row["bangumi_episode_id"],
            title=row["title"],
            title_zh=row["title_zh"],
            album_title=row["album_title"],
            artist=row["artist"],
            track_number=row["track_number"],
            disc=row["disc"],
            duration_ms=row["duration_ms"],
            subject=json.loads(row["subject_json"]),
            episode=json.loads(row["episode_json"]),
            collection=json.loads(row["collection_json"]),
        )


def clean_show_summary(subject: dict[str, Any]) -> str | None:
    value = subject.get("summary") or subject.get("short_summary")
    if not value:
        return None
    text = " ".join(str(value).split())
    return text or None


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
