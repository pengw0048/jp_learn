from __future__ import annotations

import json
import posixpath
import re
import unicodedata
import zipfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree as ET

from .models import SubtitleLine, TextFile
from .paths import DEFAULT_TEXTS_DIR


SENTENCE_RE = re.compile(r".+?(?:[。！？!?]+[」』”’）)]*|$)", re.S)
EPUB_DOC_SUFFIXES = (".xhtml", ".html", ".htm")
SUPPORTED_TEXT_SUFFIXES = {".txt", ".epub"}


@dataclass(frozen=True)
class EPUBMetadata:
    title: str | None = None
    creator: str | None = None


def discover_text_files(directory: Path = DEFAULT_TEXTS_DIR) -> list[TextFile]:
    if not directory.exists():
        return []
    return [
        text_file_from_path(path, root=directory)
        for path in sorted(directory.rglob("*"))
        if path.is_file() and path.suffix.lower() in SUPPORTED_TEXT_SUFFIXES
    ]


def text_file_from_path(path: Path, *, root: Path | None = None) -> TextFile:
    name = normalize_display_text(path.name)
    if root:
        try:
            name = normalize_display_text(str(path.relative_to(root)))
        except ValueError:
            name = normalize_display_text(path.name)
    metadata = (
        read_epub_metadata(path)
        if path.suffix.lower() == ".epub"
        else read_text_sidecar_metadata(path)
    )
    title = metadata.title or normalize_display_text(path.stem)
    return TextFile(title=title, path=path, name=name, author=metadata.creator)


def parse_text(path: Path) -> list[SubtitleLine]:
    text = read_epub_text(path) if path.suffix.lower() == ".epub" else read_text_file(path)
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


def read_epub_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        rootfile = epub_rootfile_path(archive)
        content_paths = epub_spine_paths(archive, rootfile) if rootfile else []
        if not content_paths:
            content_paths = sorted(
                name
                for name in names
                if name.lower().endswith(EPUB_DOC_SUFFIXES)
            )
        chunks = [
            extract_html_text(decode_epub_member(archive.read(name)))
            for name in content_paths
            if name in names
        ]
    return "\n\n".join(chunk for chunk in chunks if chunk)


def read_epub_metadata(path: Path) -> EPUBMetadata:
    try:
        with zipfile.ZipFile(path) as archive:
            rootfile = epub_rootfile_path(archive)
            if not rootfile:
                return EPUBMetadata()
            try:
                root = ET.fromstring(archive.read(rootfile))
            except (KeyError, ET.ParseError):
                return EPUBMetadata()
    except (OSError, zipfile.BadZipFile):
        return EPUBMetadata()
    return EPUBMetadata(
        title=first_child_text(root, ".//{*}metadata/{*}title"),
        creator=first_child_text(root, ".//{*}metadata/{*}creator"),
    )


def read_text_sidecar_metadata(path: Path) -> EPUBMetadata:
    metadata_path = path.with_name(f"{path.stem}.meta.json")
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return EPUBMetadata()
    if not isinstance(payload, dict):
        return EPUBMetadata()
    title = normalize_display_text(payload.get("title") or "")
    creator = normalize_display_text(payload.get("author") or payload.get("creator") or "")
    if not creator:
        creator = domain_from_url(payload.get("url"))
    return EPUBMetadata(title=title or None, creator=creator or None)


def domain_from_url(value: object) -> str:
    try:
        parsed = urlparse(str(value or ""))
    except ValueError:
        return ""
    hostname = normalize_display_text(parsed.hostname or "")
    return hostname[4:] if hostname.startswith("www.") else hostname


def epub_rootfile_path(archive: zipfile.ZipFile) -> str | None:
    try:
        container = archive.read("META-INF/container.xml")
    except KeyError:
        return None
    try:
        root = ET.fromstring(container)
    except ET.ParseError:
        return None
    rootfile = root.find(".//{*}rootfile")
    if rootfile is None:
        return None
    path = rootfile.attrib.get("full-path")
    return normalize_epub_path(path) if path else None


def epub_spine_paths(archive: zipfile.ZipFile, rootfile: str) -> list[str]:
    try:
        root = ET.fromstring(archive.read(rootfile))
    except (KeyError, ET.ParseError):
        return []
    base = posixpath.dirname(rootfile)
    manifest = {
        item.attrib.get("id"): item
        for item in root.findall(".//{*}manifest/{*}item")
        if item.attrib.get("id")
    }
    paths: list[str] = []
    for itemref in root.findall(".//{*}spine/{*}itemref"):
        if itemref.attrib.get("linear") == "no":
            continue
        item = manifest.get(itemref.attrib.get("idref"))
        if item is None:
            continue
        media_type = item.attrib.get("media-type", "")
        href = item.attrib.get("href")
        if not href or not is_epub_document(href, media_type):
            continue
        paths.append(normalize_epub_path(posixpath.join(base, href)))
    return paths


def is_epub_document(href: str, media_type: str) -> bool:
    if media_type in {"application/xhtml+xml", "text/html"}:
        return True
    return href.lower().split("#", 1)[0].endswith(EPUB_DOC_SUFFIXES)


def normalize_epub_path(path: str) -> str:
    path = unquote(path.split("#", 1)[0])
    return posixpath.normpath(path).lstrip("/")


def decode_epub_member(payload: bytes) -> str:
    prefix = payload[:300]
    match = re.search(br"encoding=[\"']([^\"']+)[\"']", prefix, re.I)
    encodings = [match.group(1).decode("ascii", errors="ignore")] if match else []
    encodings.extend(["utf-8-sig", "utf-8", "cp932"])
    for encoding in encodings:
        if not encoding:
            continue
        try:
            return payload.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return payload.decode("utf-8", errors="replace")


def extract_html_text(value: str) -> str:
    parser = EPUBTextExtractor()
    parser.feed(value)
    parser.close()
    return parser.text()


def first_child_text(root: ET.Element, path: str) -> str | None:
    for element in root.findall(path):
        value = normalize_display_text("".join(element.itertext()))
        if value:
            return value
    return None


def normalize_display_text(value: str) -> str:
    normalized = unicodedata.normalize("NFC", str(value or ""))
    return re.sub(r"[\s　]+", " ", normalized).strip()


def normalize_paragraph(value: str) -> str:
    return re.sub(r"[ \t　]+", " ", value.strip())


def split_sentences(paragraph: str) -> list[str]:
    sentences = [
        re.sub(r"\s*\n\s*", "", match.group(0)).strip()
        for match in SENTENCE_RE.finditer(paragraph)
    ]
    return [sentence for sentence in sentences if sentence]


class EPUBTextExtractor(HTMLParser):
    BLOCK_TAGS = {
        "address",
        "article",
        "aside",
        "blockquote",
        "br",
        "dd",
        "div",
        "dl",
        "dt",
        "figcaption",
        "figure",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hr",
        "li",
        "main",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "td",
        "th",
        "tr",
        "ul",
    }
    SKIP_TAGS = {"head", "nav", "script", "style", "svg", "title", "rt", "rp"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, _attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
            return
        if tag in self.BLOCK_TAGS:
            self._break()

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if tag in self.BLOCK_TAGS:
            self._break()

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = re.sub(r"\s+", " ", data)
        if text.strip():
            self._parts.append(text)

    def text(self) -> str:
        raw = "".join(self._parts)
        raw = re.sub(r"[ \t　]*\n[ \t　]*", "\n", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()

    def _break(self) -> None:
        if self._parts and not self._parts[-1].endswith("\n"):
            self._parts.append("\n\n")
