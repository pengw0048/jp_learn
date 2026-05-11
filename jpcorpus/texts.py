from __future__ import annotations

import re
from pathlib import Path

from .models import SubtitleLine, TextFile
from .paths import DEFAULT_TEXTS_DIR


SENTENCE_RE = re.compile(r".+?(?:[。！？!?]+[」』”’）)]*|$)", re.S)


def discover_text_files(directory: Path = DEFAULT_TEXTS_DIR) -> list[TextFile]:
    if not directory.exists():
        return []
    return [
        text_file_from_path(path, root=directory)
        for path in sorted(directory.rglob("*.txt"))
        if path.is_file()
    ]


def text_file_from_path(path: Path, *, root: Path | None = None) -> TextFile:
    name = path.name
    if root:
        try:
            name = str(path.relative_to(root))
        except ValueError:
            name = path.name
    return TextFile(title=path.stem, path=path, name=name)


def parse_text(path: Path) -> list[SubtitleLine]:
    text = read_text_file(path)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = re.split(r"\n\s*\n+", text)
    lines: list[SubtitleLine] = []
    for paragraph in paragraphs:
        paragraph = normalize_paragraph(paragraph)
        if not paragraph:
            continue
        for sentence in split_sentences(paragraph):
            lines.append(SubtitleLine(text=sentence))
    return lines


def read_text_file(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp932"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def normalize_paragraph(value: str) -> str:
    return re.sub(r"[ \t　]+", " ", value.strip())


def split_sentences(paragraph: str) -> list[str]:
    sentences = [
        re.sub(r"\s*\n\s*", "", match.group(0)).strip()
        for match in SENTENCE_RE.finditer(paragraph)
    ]
    return [sentence for sentence in sentences if sentence]
