from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Iterable

from .models import SubtitleLine


SRT_TIME_RE = re.compile(
    r"(?P<start>\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})\s*-->\s*(?P<end>\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})"
)
JAPANESE_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff々〆ヵヶ]")


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp932", "shift_jis"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="ignore")


def timestamp_to_ms(value: str) -> int:
    hours, minutes, rest = value.replace(",", ".").split(":")
    seconds, millis = rest.split(".")
    return (
        int(hours) * 3_600_000
        + int(minutes) * 60_000
        + int(seconds) * 1_000
        + int(millis.ljust(3, "0")[:3])
    )


def clean_subtitle_text(text: str) -> str:
    text = text.replace("\\N", "\n").replace("\\n", "\n")
    text = re.sub(r"\{[^}]*\}", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        lines.append(line)
    return " ".join(lines)


def contains_japanese(text: str) -> bool:
    return bool(JAPANESE_RE.search(text))


def parse_srt(path: Path) -> list[SubtitleLine]:
    text = read_text(path)
    blocks = re.split(r"\n\s*\n", text.strip())
    lines: list[SubtitleLine] = []
    for block in blocks:
        parts = [part.strip("\ufeff") for part in block.splitlines() if part.strip()]
        time_index = next((idx for idx, part in enumerate(parts) if SRT_TIME_RE.search(part)), None)
        if time_index is None:
            continue
        match = SRT_TIME_RE.search(parts[time_index])
        if not match:
            continue
        body = clean_subtitle_text("\n".join(parts[time_index + 1 :]))
        if body and contains_japanese(body):
            lines.append(
                SubtitleLine(
                    text=body,
                    start_ms=timestamp_to_ms(match.group("start")),
                    end_ms=timestamp_to_ms(match.group("end")),
                )
            )
    return lines


def parse_ass(path: Path) -> list[SubtitleLine]:
    text = read_text(path)
    in_events = False
    format_fields: list[str] = []
    lines: list[SubtitleLine] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("["):
            in_events = line.casefold() == "[events]"
            continue
        if not in_events:
            continue
        if line.casefold().startswith("format:"):
            format_fields = [field.strip().casefold() for field in line.split(":", 1)[1].split(",")]
            continue
        if not line.casefold().startswith("dialogue:"):
            continue
        payload = line.split(":", 1)[1].lstrip()
        text_index = format_fields.index("text") if "text" in format_fields else 9
        columns = payload.split(",", text_index)
        if len(columns) <= text_index:
            continue
        body = clean_subtitle_text(columns[text_index])
        if body and contains_japanese(body):
            lines.append(SubtitleLine(text=body))
    return lines


def parse_subtitle(path: Path) -> list[SubtitleLine]:
    suffix = path.suffix.casefold()
    if suffix == ".srt":
        return parse_srt(path)
    if suffix in {".ass", ".ssa"}:
        return parse_ass(path)
    return []


def iter_subtitle_lines(paths: Iterable[Path]) -> Iterable[tuple[Path, SubtitleLine]]:
    for path in paths:
        for line in parse_subtitle(path):
            yield path, line

