from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import SubtitleFile, WatchedShow
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
                SELECT sf.*, ws.title_jp, ws.title_zh
                FROM subtitle_files sf
                JOIN watched_shows ws ON ws.bangumi_id = sf.bangumi_id
                ORDER BY ws.title_jp, sf.name
                """
            ).fetchall()
        return [
            SubtitleFile(
                bangumi_id=int(row["bangumi_id"]),
                show_title=row["title_zh"] or row["title_jp"],
                path=Path(row["local_path"]),
                name=row["name"],
                episode=row["episode"],
                url=row["url"],
            )
            for row in rows
        ]

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

