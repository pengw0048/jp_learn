from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

import httpx

from .paths import ensure_dir


SUPPORTED_SUBTITLE_EXTENSIONS = {".srt", ".ass", ".ssa"}


@dataclass(frozen=True)
class JimakuEntry:
    id: int
    name: str
    anilist_id: int | None


@dataclass(frozen=True)
class JimakuFile:
    name: str
    url: str
    size: int | None = None


@dataclass(frozen=True)
class DownloadedSubtitle:
    entry: JimakuEntry
    file: JimakuFile
    path: Path
    episode: int | None


def safe_filename(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
    return cleaned or "untitled"


def extension_from_url(url: str) -> str:
    return Path(unquote(urlparse(url).path)).suffix.lower()


def parse_episode_from_filename(name: str) -> int | None:
    patterns = [
        r"[Ss]\d+[Ee](\d{1,4})",
        r"(?:^|[^\d])(?:第)?(\d{1,4})(?:話|集|[Vv]\d|\s|\.|-|_|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, name)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
    return None


def subtitle_rank(file: JimakuFile) -> tuple[int, int, str]:
    name = file.name.casefold()
    ext = extension_from_url(file.url)
    language_bonus = 0
    if any(marker in name for marker in (".ja", ".jpn", "japanese", "日本語")):
        language_bonus -= 20
    if any(marker in name for marker in (".en", "english", "chs", "cht", "中文")):
        language_bonus += 20
    generated_penalty = 10 if "generated" in name or "whisper" in name else 0
    ext_penalty = 0 if ext == ".srt" else 2
    return (language_bonus + generated_penalty + ext_penalty, len(name), name)


class JimakuClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://jimaku.cc",
        user_agent: str = "peng/jpcorpus-v0.1",
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": self.api_key,
            "User-Agent": self.user_agent,
        }

    def search(
        self,
        *,
        anilist_id: int | None = None,
        query: str | None = None,
        anime: bool = True,
    ) -> list[JimakuEntry]:
        if anilist_id is None and not query:
            raise ValueError("Jimaku search needs an AniList ID or query.")
        params: dict[str, str | int | bool] = {"anime": str(anime).lower()}
        if anilist_id is not None:
            params["anilist_id"] = anilist_id
        else:
            params["query"] = query or ""
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                f"{self.base_url}/api/entries/search",
                headers=self._headers(),
                params=params,
            )
            response.raise_for_status()
            data = response.json()
        return [
            JimakuEntry(
                id=int(item["id"]),
                name=item.get("name") or "",
                anilist_id=item.get("anilist_id"),
            )
            for item in data
        ]

    def files(self, entry_id: int, *, episode: int | None = None) -> list[JimakuFile]:
        params = {"episode": episode} if episode is not None else None
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(
                f"{self.base_url}/api/entries/{entry_id}/files",
                headers=self._headers(),
                params=params,
            )
            response.raise_for_status()
            data = response.json()
        return [
            JimakuFile(
                name=item.get("name") or Path(urlparse(item.get("url") or "").path).name,
                url=item["url"],
                size=item.get("size"),
            )
            for item in data
        ]

    def download_file(self, file: JimakuFile, destination_dir: Path) -> Path:
        ensure_dir(destination_dir)
        raw_name = file.name or Path(unquote(urlparse(file.url).path)).name
        destination = destination_dir / safe_filename(raw_name)
        if destination.exists():
            return destination
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            response = client.get(file.url, headers={"User-Agent": self.user_agent})
            response.raise_for_status()
            destination.write_bytes(response.content)
        return destination

    def download_for_show(
        self,
        *,
        title: str,
        cache_dir: Path,
        anilist_id: int | None = None,
        max_files: int = 24,
    ) -> list[DownloadedSubtitle]:
        entries = self.search(anilist_id=anilist_id, query=title if anilist_id is None else None)
        if not entries and anilist_id is not None:
            entries = self.search(query=title)
        if not entries:
            return []

        entry = entries[0]
        files = [
            file
            for file in self.files(entry.id)
            if extension_from_url(file.url) in SUPPORTED_SUBTITLE_EXTENSIONS
        ]
        files.sort(key=subtitle_rank)
        chosen = files[:max_files]
        show_dir = cache_dir / safe_filename(entry.name or title)
        downloads = []
        for file in chosen:
            path = self.download_file(file, show_dir)
            downloads.append(
                DownloadedSubtitle(
                    entry=entry,
                    file=file,
                    path=path,
                    episode=parse_episode_from_filename(file.name),
                )
            )
        return downloads

