from __future__ import annotations

import secrets
import time
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from .models import MusicTrack, WatchedShow


API_BASE = "https://api.bgm.tv"
OAUTH_BASE = "https://bgm.tv"
SUBJECT_ANIME = 2
SUBJECT_MUSIC = 3
COLLECTION_DONE = 2


@dataclass(frozen=True)
class OAuthResult:
    token: dict[str, Any]
    expires_at: int | None


def extract_year(date_text: str | None) -> int | None:
    if not date_text or len(date_text) < 4:
        return None
    try:
        return int(date_text[:4])
    except ValueError:
        return None


class BangumiClient:
    def __init__(
        self,
        *,
        access_token: str | None = None,
        user_agent: str = "peng/jpcorpus-v0.1",
        timeout: float = 30.0,
    ) -> None:
        self.access_token = access_token
        self.user_agent = user_agent
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {"User-Agent": self.user_agent}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def me(self) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(f"{API_BASE}/v0/me", headers=self._headers())
            response.raise_for_status()
            return response.json()

    def watched_collections(
        self,
        username: str,
        *,
        subject_type: int = SUBJECT_ANIME,
        page_size: int = 50,
        max_items: int | None = None,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        offset = 0
        with httpx.Client(timeout=self.timeout) as client:
            while True:
                params = {
                    "subject_type": subject_type,
                    "type": COLLECTION_DONE,
                    "limit": page_size,
                    "offset": offset,
                }
                response = client.get(
                    f"{API_BASE}/v0/users/{username}/collections",
                    headers=self._headers(),
                    params=params,
                )
                response.raise_for_status()
                payload = response.json()
                batch = payload.get("data", [])
                items.extend(batch)
                if max_items is not None and len(items) >= max_items:
                    return items[:max_items]
                if not batch or len(batch) < page_size:
                    return items
                total = payload.get("total")
                offset += len(batch)
                if isinstance(total, int) and offset >= total:
                    return items

    def episodes(
        self,
        subject_id: int,
        *,
        page_size: int = 100,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        offset = 0
        with httpx.Client(timeout=self.timeout) as client:
            while True:
                response = client.get(
                    f"{API_BASE}/v0/episodes",
                    headers=self._headers(),
                    params={"subject_id": subject_id, "limit": page_size, "offset": offset},
                )
                response.raise_for_status()
                payload = response.json()
                batch = payload.get("data", [])
                items.extend(batch)
                if not batch or len(batch) < page_size:
                    return items
                total = payload.get("total")
                offset += len(batch)
                if isinstance(total, int) and offset >= total:
                    return items

    def token_from_code(
        self,
        *,
        client_id: str,
        client_secret: str,
        code: str,
        redirect_uri: str,
    ) -> OAuthResult:
        data = {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{OAUTH_BASE}/oauth/access_token",
                data=data,
                headers={"User-Agent": self.user_agent},
            )
            response.raise_for_status()
            token = response.json()
        expires_in = token.get("expires_in")
        expires_at = int(time.time() + int(expires_in)) if expires_in else None
        return OAuthResult(token=token, expires_at=expires_at)


def collection_to_show(item: dict[str, Any]) -> WatchedShow:
    subject = item.get("subject") or {}
    bangumi_id = item.get("subject_id") or subject.get("id")
    if bangumi_id is None:
        raise ValueError(f"Collection item has no subject ID: {item!r}")

    title_jp = subject.get("name") or f"Bangumi {bangumi_id}"
    title_zh = subject.get("name_cn") or None
    air_date = subject.get("date") or None
    return WatchedShow(
        bangumi_id=int(bangumi_id),
        title_jp=title_jp,
        title_zh=title_zh,
        air_date=air_date,
        year=extract_year(air_date),
        ep_status=item.get("ep_status"),
        subject=subject,
        collection=item,
    )


def collection_to_music_tracks(
    item: dict[str, Any],
    episodes: list[dict[str, Any]],
) -> list[MusicTrack]:
    subject = item.get("subject") or {}
    bangumi_id = item.get("subject_id") or subject.get("id")
    if bangumi_id is None:
        raise ValueError(f"Collection item has no subject ID: {item!r}")

    album_title = subject.get("name") or subject.get("name_cn") or f"Bangumi {bangumi_id}"
    artist = extract_artist(subject)
    tracks = []
    for episode in episodes:
        title = episode.get("name") or episode.get("name_cn")
        if not title:
            continue
        episode_id = episode.get("id")
        track_key = (
            f"bangumi:{int(bangumi_id)}:ep:{int(episode_id)}"
            if episode_id is not None
            else f"bangumi:{int(bangumi_id)}:track:{len(tracks) + 1}"
        )
        tracks.append(
            MusicTrack(
                track_key=track_key,
                bangumi_id=int(bangumi_id),
                title=title,
                title_zh=episode.get("name_cn") or None,
                album_title=album_title,
                artist=artist,
                bangumi_episode_id=int(episode_id) if episode_id is not None else None,
                track_number=coerce_int(episode.get("sort") or episode.get("ep")),
                disc=coerce_int(episode.get("disc")),
                duration_ms=parse_duration_ms(episode.get("duration_seconds") or episode.get("duration")),
                subject=subject,
                episode=episode,
                collection=item,
            )
        )
    if tracks:
        return tracks
    return [
        MusicTrack(
            track_key=f"bangumi:{int(bangumi_id)}:subject",
            bangumi_id=int(bangumi_id),
            title=album_title,
            album_title=album_title,
            artist=artist,
            subject=subject,
            collection=item,
        )
    ]


def extract_artist(subject: dict[str, Any]) -> str | None:
    keys = {
        "artist",
        "artists",
        "アーティスト",
        "歌手",
        "演唱",
        "艺术家",
        "藝人",
        "作词",
        "作詞",
        "作曲",
    }
    for item in subject.get("infobox") or []:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "").strip().casefold()
        if key not in {candidate.casefold() for candidate in keys}:
            continue
        value = normalize_infobox_value(item.get("value"))
        if value:
            return value
    return None


def normalize_infobox_value(value: Any) -> str | None:
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                part = item.get("v") or item.get("name") or item.get("title")
            else:
                part = item
            if part:
                parts.append(str(part).strip())
        text = ", ".join(part for part in parts if part)
    else:
        text = str(value or "").strip()
    return text or None


def coerce_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def parse_duration_ms(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return int(float(value) * 1000)
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        return int(text) * 1000
    parts = text.split(":")
    if not all(part.isdigit() for part in parts):
        return None
    seconds = 0
    for part in parts:
        seconds = seconds * 60 + int(part)
    return seconds * 1000


class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    server: "_OAuthServer"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        query = parse_qs(urlparse(self.path).query)
        state = query.get("state", [None])[0]
        code = query.get("code", [None])[0]
        error = query.get("error", [None])[0]
        if state != self.server.expected_state:
            self.server.error = "OAuth state mismatch."
            self._reply(400, "OAuth state mismatch. You can close this tab.")
            return
        if error:
            self.server.error = error
            self._reply(400, f"Bangumi returned an error: {error}")
            return
        if not code:
            self.server.error = "Missing OAuth code."
            self._reply(400, "Missing OAuth code. You can close this tab.")
            return
        self.server.code = code
        self._reply(200, "Bangumi linked. You can close this tab and return to the terminal.")

    def _reply(self, status: int, message: str) -> None:
        body = message.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class _OAuthServer(HTTPServer):
    code: str | None = None
    error: str | None = None

    def __init__(self, server_address: tuple[str, int], state: str) -> None:
        self.expected_state = state
        super().__init__(server_address, _OAuthCallbackHandler)


def run_oauth_flow(
    *,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    user_agent: str,
    open_browser: bool = True,
) -> OAuthResult:
    parsed = urlparse(redirect_uri)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    host = parsed.hostname or "127.0.0.1"
    state = secrets.token_urlsafe(24)
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "state": state,
    }
    authorize_url = f"{OAUTH_BASE}/oauth/authorize?{urlencode(params)}"
    print(f"Open this URL to authorize Bangumi:\n{authorize_url}")
    if open_browser:
        webbrowser.open(authorize_url)

    server = _OAuthServer((host, port), state)
    server.handle_request()
    if server.error:
        raise RuntimeError(server.error)
    if not server.code:
        raise RuntimeError("OAuth callback did not receive a code.")

    client = BangumiClient(user_agent=user_agent)
    return client.token_from_code(
        client_id=client_id,
        client_secret=client_secret,
        code=server.code,
        redirect_uri=redirect_uri,
    )
