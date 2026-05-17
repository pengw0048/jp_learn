from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
import sqlite3
import struct
import unicodedata
import zipfile
from collections.abc import Iterable
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, BinaryIO

from .paths import DEFAULT_USER_DICTIONARY_DIR, ensure_dir


REGISTRY_SCHEMA_VERSION = 1
INDEX_SCHEMA_VERSION = 1
SUPPORTED_DICTIONARY_FORMATS = {"yomitan", "mdx"}
MAX_LOOKUP_TEXT_CHARS = 5000
_MDX_CACHE: dict[tuple[str, float], Any] = {}


class DictionaryImportError(ValueError):
    pass


def dictionary_registry_status(*, base_dir: Path = DEFAULT_USER_DICTIONARY_DIR) -> dict[str, Any]:
    registry = load_dictionary_registry(base_dir=base_dir)
    return {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "storage_dir": str(base_dir),
        "dictionaries": [public_dictionary_record(record) for record in registry["dictionaries"]],
    }


def load_dictionary_registry(*, base_dir: Path = DEFAULT_USER_DICTIONARY_DIR) -> dict[str, Any]:
    path = dictionary_registry_path(base_dir)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        payload = {}
    dictionaries = payload.get("dictionaries") if isinstance(payload, dict) else []
    if not isinstance(dictionaries, list):
        dictionaries = []
    return {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "dictionaries": [
            normalize_dictionary_record(record)
            for record in dictionaries
            if isinstance(record, dict) and record.get("id")
        ],
    }


def save_dictionary_registry(registry: dict[str, Any], *, base_dir: Path = DEFAULT_USER_DICTIONARY_DIR) -> dict[str, Any]:
    payload = {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "dictionaries": [
            normalize_dictionary_record(record)
            for record in registry.get("dictionaries", [])
            if isinstance(record, dict) and record.get("id")
        ],
    }
    path = dictionary_registry_path(base_dir)
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def dictionary_registry_path(base_dir: Path = DEFAULT_USER_DICTIONARY_DIR) -> Path:
    return Path(base_dir) / "registry.json"


def import_dictionary_upload(
    *,
    filename: str,
    stream: BinaryIO,
    name: str | None = None,
    base_dir: Path = DEFAULT_USER_DICTIONARY_DIR,
) -> dict[str, Any]:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in {".zip", ".mdx"}:
        raise DictionaryImportError("Only Yomitan .zip and MDX .mdx dictionaries are supported.")
    upload_dir = ensure_dir(Path(base_dir) / "_uploads")
    temp_path = upload_dir / f"{safe_slug(Path(filename).stem or 'dictionary')}-{_now_compact()}{suffix}"
    content_hash = _copy_stream_with_hash(stream, temp_path)
    try:
        result = import_dictionary_file(temp_path, name=name, base_dir=base_dir, content_hash=content_hash)
    finally:
        try:
            temp_path.unlink()
        except OSError:
            pass
    return result


def import_dictionary_file(
    source_path: Path,
    *,
    name: str | None = None,
    base_dir: Path = DEFAULT_USER_DICTIONARY_DIR,
    content_hash: str | None = None,
) -> dict[str, Any]:
    source_path = Path(source_path).expanduser().resolve()
    if not source_path.is_file():
        raise DictionaryImportError(f"Dictionary file not found: {source_path}")
    dictionary_format = detect_dictionary_format(source_path)
    if content_hash is None:
        content_hash = file_sha256(source_path)

    registry = load_dictionary_registry(base_dir=base_dir)
    existing = next(
        (
            record
            for record in registry["dictionaries"]
            if record.get("content_hash") == content_hash and record.get("format") == dictionary_format
        ),
        None,
    )
    if existing:
        if name:
            existing["name"] = name.strip()
        elif dictionary_name_needs_refresh(existing):
            existing["name"] = dictionary_title_from_source(source_path, dictionary_format)
        if dictionary_index_is_ready(existing):
            existing["updated_at"] = _now_iso()
            registry = save_dictionary_registry(registry, base_dir=base_dir)
            return {
                "imported": False,
                "dictionary": public_dictionary_record(existing),
                "dictionaries": dictionary_registry_status(base_dir=base_dir),
            }
        ensure_dictionary_source(existing, source_path, base_dir=base_dir)
        try:
            existing["status"] = "indexing"
            existing["error"] = ""
            existing["updated_at"] = _now_iso()
            save_dictionary_registry(registry, base_dir=base_dir)
            stats = build_dictionary_index(existing)
            existing["status"] = "ready"
            existing["stats"] = stats
            existing["error"] = ""
        except Exception as exc:
            existing["status"] = "error"
            existing["error"] = str(exc)
            existing["stats"] = {}
            raise
        finally:
            existing["updated_at"] = _now_iso()
            registry = save_dictionary_registry(registry, base_dir=base_dir)
        return {
            "imported": True,
            "dictionary": public_dictionary_record(existing),
            "dictionaries": dictionary_registry_status(base_dir=base_dir),
        }

    title = name.strip() if name else dictionary_title_from_source(source_path, dictionary_format)
    record_id = unique_dictionary_id(title, content_hash, registry)
    destination_dir = ensure_dir(Path(base_dir) / record_id)
    destination_source = destination_dir / f"source{source_path.suffix.lower()}"
    shutil.copy2(source_path, destination_source)
    index_path = destination_dir / "index.sqlite3"

    record = {
        "id": record_id,
        "name": title,
        "format": dictionary_format,
        "enabled": True,
        "priority": next_dictionary_priority(registry),
        "source_path": str(destination_source),
        "source_file": source_path.name,
        "index_path": str(index_path),
        "content_hash": content_hash,
        "status": "indexing",
        "error": "",
        "stats": {},
        "imported_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    registry["dictionaries"].append(record)
    try:
        stats = build_dictionary_index(record)
        record["status"] = "ready"
        record["stats"] = stats
        record["error"] = ""
    except Exception as exc:
        record["status"] = "error"
        record["error"] = str(exc)
        record["stats"] = {}
        raise
    finally:
        record["updated_at"] = _now_iso()
        registry = save_dictionary_registry(registry, base_dir=base_dir)

    return {
        "imported": True,
        "dictionary": public_dictionary_record(record),
        "dictionaries": dictionary_registry_status(base_dir=base_dir),
    }


def update_dictionary_record(
    dictionary_id: str,
    updates: dict[str, Any],
    *,
    base_dir: Path = DEFAULT_USER_DICTIONARY_DIR,
) -> dict[str, Any]:
    registry = load_dictionary_registry(base_dir=base_dir)
    record = find_dictionary_record(registry, dictionary_id)
    if "enabled" in updates:
        record["enabled"] = bool(updates["enabled"])
    if "priority" in updates:
        record["priority"] = int(updates["priority"])
    if "name" in updates:
        name = str(updates["name"] or "").strip()
        if name:
            record["name"] = name
    record["updated_at"] = _now_iso()
    save_dictionary_registry(registry, base_dir=base_dir)
    return dictionary_registry_status(base_dir=base_dir)


def delete_dictionary_record(dictionary_id: str, *, base_dir: Path = DEFAULT_USER_DICTIONARY_DIR) -> dict[str, Any]:
    registry = load_dictionary_registry(base_dir=base_dir)
    record = find_dictionary_record(registry, dictionary_id)
    registry["dictionaries"] = [item for item in registry["dictionaries"] if item.get("id") != dictionary_id]
    save_dictionary_registry(registry, base_dir=base_dir)
    source_dir = Path(record.get("source_path") or "").parent
    if source_dir.name == dictionary_id and source_dir.exists():
        shutil.rmtree(source_dir, ignore_errors=True)
    return dictionary_registry_status(base_dir=base_dir)


def reindex_dictionary_record(dictionary_id: str, *, base_dir: Path = DEFAULT_USER_DICTIONARY_DIR) -> dict[str, Any]:
    registry = load_dictionary_registry(base_dir=base_dir)
    record = find_dictionary_record(registry, dictionary_id)
    try:
        record["stats"] = build_dictionary_index(record)
        record["status"] = "ready"
        record["error"] = ""
    except Exception as exc:
        record["status"] = "error"
        record["error"] = str(exc)
        raise
    finally:
        record["updated_at"] = _now_iso()
        save_dictionary_registry(registry, base_dir=base_dir)
    return dictionary_registry_status(base_dir=base_dir)


def dictionary_index_is_ready(record: dict[str, Any]) -> bool:
    return record.get("status") == "ready" and Path(record.get("index_path") or "").is_file()


def dictionary_name_needs_refresh(record: dict[str, Any]) -> bool:
    name = str(record.get("name") or "").strip()
    return not name or re.search(r"-\d{20}$", name) is not None


def ensure_dictionary_source(
    record: dict[str, Any],
    source_path: Path,
    *,
    base_dir: Path = DEFAULT_USER_DICTIONARY_DIR,
) -> None:
    record_id = str(record.get("id") or "").strip()
    if record.get("source_path"):
        destination_dir = ensure_dir(Path(record["source_path"]).parent)
    else:
        destination_dir = ensure_dir(Path(base_dir) / record_id)
    destination_source = Path(record.get("source_path") or destination_dir / f"source{source_path.suffix.lower()}")
    if not record.get("source_path"):
        record["source_path"] = str(destination_source)
    if not record.get("index_path"):
        record["index_path"] = str(destination_dir / "index.sqlite3")
    record["source_file"] = source_path.name
    if not destination_source.is_file():
        shutil.copy2(source_path, destination_source)


def lookup_user_dictionaries(
    word: dict[str, Any] | str,
    *,
    base_dir: Path = DEFAULT_USER_DICTIONARY_DIR,
    limit_per_dictionary: int = 8,
) -> list[dict[str, Any]]:
    candidates = dictionary_lookup_candidates(word)
    primary_terms = dictionary_primary_lookup_terms(word)
    if not candidates:
        return []
    registry = load_dictionary_registry(base_dir=base_dir)
    results: list[dict[str, Any]] = []
    for record in enabled_dictionary_records(registry):
        if len(results) >= 24:
            break
        try:
            results.extend(lookup_one_dictionary(record, candidates, primary_terms=primary_terms, limit=limit_per_dictionary))
        except Exception:
            continue
    return results


def attach_user_dictionary_results(word: dict[str, Any]) -> dict[str, Any]:
    word["user_dictionary_results"] = lookup_user_dictionaries(word)
    return word


def lookup_one_dictionary(
    record: dict[str, Any],
    candidates: list[str],
    *,
    primary_terms: list[str],
    limit: int,
) -> list[dict[str, Any]]:
    index_path = Path(record.get("index_path") or "")
    if record.get("status") != "ready" or not index_path.is_file():
        return []
    with sqlite3.connect(index_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = select_dictionary_rows(conn, candidates, limit=limit)
    if record.get("format") == "mdx":
        return mdx_rows_to_results(record, rows)
    return prune_yomitan_lookup_results(yomitan_rows_to_results(record, rows), primary_terms)


def prune_yomitan_lookup_results(results: list[dict[str, Any]], primary_terms: list[str]) -> list[dict[str, Any]]:
    primary_set = set(primary_terms)
    has_primary_definition = any(
        result.get("kind") != "reference" and normalize_dictionary_text(result.get("headword")) in primary_set
        for result in results
    )
    if not has_primary_definition:
        return results
    return [
        result
        for result in results
        if result.get("kind") == "reference" or normalize_dictionary_text(result.get("headword")) in primary_set
    ]


def select_dictionary_rows(conn: sqlite3.Connection, candidates: list[str], *, limit: int) -> list[sqlite3.Row]:
    rows: list[sqlite3.Row] = []
    seen_ids: set[int] = set()
    for key in candidates:
        for row in conn.execute(
            """
            SELECT id, lookup_key, headword, reading, content_json, record_offset, record_length
            FROM entries
            WHERE lookup_key = ?
            ORDER BY score DESC, id
            LIMIT ?
            """,
            (normalize_dictionary_text(key), limit),
        ):
            row_id = int(row["id"])
            if row_id in seen_ids:
                continue
            rows.append(row)
            seen_ids.add(row_id)
            if len(rows) >= limit:
                return rows
    return rows


def yomitan_rows_to_results(record: dict[str, Any], rows: Iterable[sqlite3.Row]) -> list[dict[str, Any]]:
    results = []
    seen: set[tuple[str, str, tuple[str, ...]]] = set()
    for row in rows:
        try:
            content = json.loads(row["content_json"] or "{}")
        except json.JSONDecodeError:
            content = {}
        definitions = unique_strings(content.get("definitions") or [])
        tags = unique_strings(content.get("tags") or [])
        reference_markers = unique_strings(content.get("reference_markers") or [])
        if is_yomitan_redirect_reference(tags, definitions, reference_markers):
            continue
        reference = yomitan_reference_info(tags, definitions, reference_markers)
        display_definitions = reference.get("targets") or definitions
        key = (
            str(content.get("headword") or row["headword"] or ""),
            str(content.get("reading") or row["reading"] or ""),
            tuple(display_definitions),
        )
        if key in seen:
            continue
        seen.add(key)
        text = "；".join(display_definitions)
        results.append(
            {
                "dictionary_id": record["id"],
                "dictionary_name": record["name"],
                "format": "yomitan",
                "headword": content.get("headword") or row["headword"],
                "reading": content.get("reading") or row["reading"] or "",
                "tags": tags,
                "kind": "reference" if reference else "definition",
                "reference_type": reference.get("type") or "",
                "references": reference.get("targets") or [],
                "definitions": display_definitions,
                "text": text,
            }
        )
    return results


def mdx_rows_to_results(record: dict[str, Any], rows: Iterable[sqlite3.Row]) -> list[dict[str, Any]]:
    source_path = Path(record.get("source_path") or "")
    if not source_path.is_file():
        return []
    mdx = cached_mdx(source_path)
    results = []
    for row in rows:
        key_hex = str(row["content_json"] or "")
        record_key = bytes.fromhex(key_hex) if key_hex else str(row["headword"] or row["lookup_key"]).encode("utf-8")
        raw = read_mdx_record(
            mdx,
            key=record_key,
            offset=int(row["record_offset"]),
            length=int(row["record_length"]),
        )
        text = truncate_text(strip_html_to_text(raw), MAX_LOOKUP_TEXT_CHARS)
        if not text:
            continue
        results.append(
            {
                "dictionary_id": record["id"],
                "dictionary_name": record["name"],
                "format": "mdx",
                "headword": row["headword"] or row["lookup_key"],
                "reading": row["reading"] or "",
                "tags": [],
                "definitions": [text],
                "text": text,
            }
        )
    return results


def build_dictionary_index(record: dict[str, Any]) -> dict[str, Any]:
    dictionary_format = record.get("format")
    if dictionary_format == "yomitan":
        return build_yomitan_index(Path(record["source_path"]), Path(record["index_path"]))
    if dictionary_format == "mdx":
        return build_mdx_index(Path(record["source_path"]), Path(record["index_path"]))
    raise DictionaryImportError(f"Unsupported dictionary format: {dictionary_format}")


def build_yomitan_index(source_path: Path, index_path: Path) -> dict[str, Any]:
    ensure_dir(index_path.parent)
    temp_path = index_path.with_suffix(".tmp.sqlite3")
    if temp_path.exists():
        temp_path.unlink()
    entry_count = 0
    lookup_count = 0
    headwords: set[str] = set()
    with sqlite3.connect(temp_path) as conn:
        create_index_tables(conn)
        with zipfile.ZipFile(source_path) as archive:
            title = yomitan_archive_title(archive) or source_path.stem
            write_index_metadata(conn, "format", "yomitan")
            write_index_metadata(conn, "title", title)
            for name in sorted(archive.namelist()):
                if not re.fullmatch(r"term_bank_\d+\.json", Path(name).name):
                    continue
                terms = json.loads(archive.read(name).decode("utf-8"))
                if not isinstance(terms, list):
                    continue
                for term in terms:
                    content = parse_yomitan_term(term)
                    if not content:
                        continue
                    entry_count += 1
                    headwords.add(content["headword"])
                    lookup_count += insert_dictionary_entry(conn, content)
        conn.commit()
    replace_file(temp_path, index_path)
    return {
        "entry_count": entry_count,
        "headword_count": len(headwords),
        "lookup_count": lookup_count,
    }


def build_mdx_index(source_path: Path, index_path: Path) -> dict[str, Any]:
    MDX = import_mdx_class()
    mdx = MDX(str(source_path))
    key_list = list(getattr(mdx, "_key_list", []) or [])
    ensure_dir(index_path.parent)
    temp_path = index_path.with_suffix(".tmp.sqlite3")
    if temp_path.exists():
        temp_path.unlink()
    headwords: set[str] = set()
    with sqlite3.connect(temp_path) as conn:
        create_index_tables(conn)
        write_index_metadata(conn, "format", "mdx")
        write_index_metadata(conn, "title", source_path.stem)
        for index, (offset, key) in enumerate(key_list):
            headword = decode_mdx_key(key)
            lookup_key = normalize_dictionary_text(headword)
            if not lookup_key:
                continue
            next_offset = int(key_list[index + 1][0]) if index + 1 < len(key_list) else -1
            length = next_offset - int(offset) if next_offset >= 0 else -1
            conn.execute(
                """
                INSERT INTO entries (
                    lookup_key, headword, reading, score, content_json, record_offset, record_length
                )
                VALUES (?, ?, '', 0, ?, ?, ?)
                """,
                (lookup_key, headword, key.hex() if isinstance(key, bytes) else "", int(offset), int(length)),
            )
            headwords.add(lookup_key)
        conn.commit()
    replace_file(temp_path, index_path)
    return {
        "entry_count": len(key_list),
        "headword_count": len(headwords),
        "lookup_count": len(key_list),
    }


def create_index_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE entries (
            id INTEGER PRIMARY KEY,
            lookup_key TEXT NOT NULL,
            headword TEXT NOT NULL,
            reading TEXT,
            score INTEGER DEFAULT 0,
            content_json TEXT,
            record_offset INTEGER,
            record_length INTEGER
        )
        """
    )
    conn.execute("CREATE INDEX entries_lookup_key_idx ON entries(lookup_key)")


def write_index_metadata(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)", (key, value))


def insert_dictionary_entry(conn: sqlite3.Connection, content: dict[str, Any]) -> int:
    lookup_keys = dictionary_entry_lookup_keys(content["headword"], content.get("reading") or "")
    row_count = 0
    content_json = json.dumps(content, ensure_ascii=False, separators=(",", ":"))
    for key in lookup_keys:
        conn.execute(
            """
            INSERT INTO entries (lookup_key, headword, reading, score, content_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (key, content["headword"], content.get("reading") or "", int(content.get("score") or 0), content_json),
        )
        row_count += 1
    return row_count


def parse_yomitan_term(term: Any) -> dict[str, Any] | None:
    if not isinstance(term, list) or len(term) < 6:
        return None
    headword = normalize_dictionary_text(term[0])
    reading = normalize_dictionary_text(term[1])
    if not headword:
        return None
    definition_tags = split_tags(term[2] if len(term) > 2 else "")
    score = int(term[4] or 0) if len(term) > 4 and isinstance(term[4], int | float) else 0
    definitions = yomitan_glossary_texts(term[5])
    reference_markers = yomitan_reference_markers(term[5])
    term_tags = split_tags(term[7] if len(term) > 7 else "")
    if not definitions and not term_tags and not definition_tags:
        return None
    return {
        "headword": headword,
        "reading": reading if reading != headword else "",
        "definitions": definitions,
        "reference_markers": reference_markers,
        "tags": unique_strings([*definition_tags, *term_tags]),
        "score": score,
    }


def yomitan_archive_title(archive: zipfile.ZipFile) -> str:
    try:
        payload = json.loads(archive.read("index.json").decode("utf-8"))
    except (KeyError, json.JSONDecodeError, UnicodeDecodeError):
        return ""
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("title") or payload.get("name") or "").strip()


def dictionary_title_from_source(source_path: Path, dictionary_format: str) -> str:
    if dictionary_format == "yomitan":
        try:
            with zipfile.ZipFile(source_path) as archive:
                title = yomitan_archive_title(archive)
                if title:
                    return title
        except zipfile.BadZipFile:
            pass
    if dictionary_format == "mdx":
        title = mdx_title_from_source(source_path)
        if title:
            return title
    return source_path.stem


def mdx_title_from_source(source_path: Path) -> str:
    try:
        MDX = import_mdx_class()
        mdx = MDX(str(source_path))
    except Exception:
        return ""
    header = getattr(mdx, "header", {}) or {}
    title = decode_mdx_header_text(header.get(b"Title") or header.get("Title"))
    if title and "No HTML" not in title:
        return title
    description = strip_html_to_text(decode_mdx_header_text(header.get(b"Description") or header.get("Description")))
    match = re.search(r"《([^》]{2,80})》", description)
    if match:
        return normalize_dictionary_text(match.group(1))
    return normalize_dictionary_text(description.splitlines()[0] if description else "")


def decode_mdx_header_text(value: Any) -> str:
    if isinstance(value, bytes):
        for encoding in ("utf-8", "utf-16", "utf-16-le"):
            try:
                return value.decode(encoding).strip()
            except UnicodeDecodeError:
                continue
        return value.decode("utf-8", errors="replace").strip()
    return str(value or "").strip()


def dictionary_entry_lookup_keys(headword: str, reading: str = "") -> list[str]:
    keys = [normalize_dictionary_text(headword)]
    reading = normalize_dictionary_text(reading)
    if reading and reading != keys[0]:
        keys.append(f"{keys[0]}\t{reading}")
    return unique_strings(keys)


def dictionary_lookup_candidates(word: dict[str, Any] | str) -> list[str]:
    if isinstance(word, str):
        return [normalize_dictionary_text(word)]
    values = [word.get("word"), word.get("base_form"), word.get("reading")]
    notes = word.get("lexical_notes") if isinstance(word.get("lexical_notes"), dict) else {}
    for key in ("spellings", "readings"):
        for form in notes.get(key) or []:
            if isinstance(form, dict):
                values.append(form.get("text"))
            else:
                values.append(form)
    candidates = []
    word_text = normalize_dictionary_text(word.get("word"))
    reading = normalize_dictionary_text(word.get("reading"))
    if word_text and reading and word_text != reading:
        for reading_part in split_candidate_forms(reading):
            candidates.append(f"{word_text}\t{reading_part}")
    for value in values:
        candidates.extend(split_candidate_forms(value))
    return unique_strings(normalize_dictionary_text(value) for value in candidates)


def dictionary_primary_lookup_terms(word: dict[str, Any] | str) -> list[str]:
    if isinstance(word, str):
        return split_candidate_forms(word)
    values = [word.get("word"), word.get("base_form")]
    notes = word.get("lexical_notes") if isinstance(word.get("lexical_notes"), dict) else {}
    for form in notes.get("spellings") or []:
        if isinstance(form, dict):
            values.append(form.get("text"))
        else:
            values.append(form)
    candidates = []
    for value in values:
        candidates.extend(split_candidate_forms(value))
    return unique_strings(normalize_dictionary_text(value) for value in candidates)


def split_candidate_forms(value: Any) -> list[str]:
    text = normalize_dictionary_text(value)
    if not text:
        return []
    parts = [normalize_dictionary_text(part) for part in re.split(r"[;；,，、/・･\s]+", text)]
    return unique_strings([text, *parts])


def enabled_dictionary_records(registry: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        (
            record
            for record in registry.get("dictionaries", [])
            if record.get("enabled", True)
        ),
        key=lambda record: (int(record.get("priority") or 0), str(record.get("name") or "")),
    )


def find_dictionary_record(registry: dict[str, Any], dictionary_id: str) -> dict[str, Any]:
    target = str(dictionary_id or "").strip()
    for record in registry.get("dictionaries", []):
        if record.get("id") == target:
            return record
    raise DictionaryImportError(f"Dictionary not found: {target}")


def public_dictionary_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": record.get("id"),
        "name": record.get("name") or record.get("id"),
        "format": record.get("format"),
        "enabled": bool(record.get("enabled", True)),
        "priority": int(record.get("priority") or 0),
        "source_file": record.get("source_file") or Path(str(record.get("source_path") or "")).name,
        "status": record.get("status") or "ready",
        "error": record.get("error") or "",
        "stats": record.get("stats") or {},
        "imported_at": record.get("imported_at") or "",
        "updated_at": record.get("updated_at") or "",
    }


def normalize_dictionary_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(record.get("id") or "").strip(),
        "name": str(record.get("name") or record.get("id") or "").strip(),
        "format": str(record.get("format") or "").strip(),
        "enabled": bool(record.get("enabled", True)),
        "priority": int(record.get("priority") or 0),
        "source_path": str(record.get("source_path") or ""),
        "source_file": str(record.get("source_file") or ""),
        "index_path": str(record.get("index_path") or ""),
        "content_hash": str(record.get("content_hash") or ""),
        "status": str(record.get("status") or "ready"),
        "error": str(record.get("error") or ""),
        "stats": record.get("stats") if isinstance(record.get("stats"), dict) else {},
        "imported_at": str(record.get("imported_at") or ""),
        "updated_at": str(record.get("updated_at") or ""),
    }


def detect_dictionary_format(source_path: Path) -> str:
    suffix = Path(source_path).suffix.lower()
    if suffix == ".zip":
        return "yomitan"
    if suffix == ".mdx":
        return "mdx"
    raise DictionaryImportError("Only Yomitan .zip and MDX .mdx dictionaries are supported.")


def yomitan_glossary_texts(value: Any) -> list[str]:
    primary = _extract_yomitan_primary_glosses(value)
    if primary:
        return unique_strings(primary)
    return unique_strings(clean_yomitan_definition(text) for text in _flatten_yomitan_glossary(value))


def _extract_yomitan_primary_glosses(value: Any) -> list[str]:
    glosses: list[str] = []
    for node in _find_yomitan_gloss_lists(value):
        content = node.get("content")
        items = content if isinstance(content, list) else [content]
        for item in items:
            glosses.extend(clean_yomitan_definitions(_yomitan_structured_text(item)))
    return glosses


def _find_yomitan_gloss_lists(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        results: list[dict[str, Any]] = []
        for item in value:
            results.extend(_find_yomitan_gloss_lists(item))
        return results
    if not isinstance(value, dict):
        return []
    data = value.get("data") if isinstance(value.get("data"), dict) else {}
    if data.get("content") == "glosses":
        return [value]
    results = []
    for key in ("content", "children"):
        if key in value:
            results.extend(_find_yomitan_gloss_lists(value[key]))
    return results


def _yomitan_structured_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return html.unescape(value)
    if isinstance(value, int | float | bool):
        return str(value)
    if isinstance(value, list):
        return "".join(_yomitan_structured_text(item) for item in value)
    if isinstance(value, dict):
        data = value.get("data") if isinstance(value.get("data"), dict) else {}
        marker = str(data.get("content") or "")
        if marker in {
            "backlink",
            "details-entry-examples",
            "example-sentence",
            "example-sentence-a",
            "example-sentence-b",
            "extra-info",
            "tags",
        }:
            return ""
        for key in ("content", "children", "text"):
            if key in value:
                return _yomitan_structured_text(value[key])
    return ""


def clean_yomitan_definition(value: Any) -> str:
    definitions = clean_yomitan_definitions(value)
    return definitions[0] if definitions else ""


def clean_yomitan_definitions(value: Any) -> list[str]:
    numbered = extract_numbered_yomitan_definitions(str(value or ""))
    if numbered:
        return numbered
    text = normalize_space(str(value or ""))
    if not text:
        return []
    if text in {"Wiktionary", "Kaikki", "|", "词源"}:
        return []
    if re.fullmatch(r"\d+\s*例", text):
        return []
    if "redirected from" in text:
        return []
    if text in {
        "n",
        "v",
        "vi",
        "vt",
        "adj",
        "adv",
        "intj",
        "godan",
        "non-lemma",
        "sl",
        "alt-of",
        "alternative kanji",
    }:
        return []
    text = strip_yomitan_headword_prefix(text)
    return [text]


def yomitan_reference_markers(value: Any) -> list[str]:
    return unique_strings(
        text
        for text in _flatten_yomitan_glossary(value)
        if text in {"alt-of", "alternative kanji"} or "redirected from" in text
    )


def extract_numbered_yomitan_definitions(value: str) -> list[str]:
    definitions = []
    for line in str(value or "").splitlines():
        text = normalize_space(line)
        match = re.match(r"^\d+[.．]\s*(.+)$", text)
        if not match:
            continue
        definition = re.sub(r"[。．.]+$", "", match.group(1).strip())
        if definition:
            definitions.append(definition)
    return unique_strings(definitions)


def strip_yomitan_headword_prefix(value: str) -> str:
    match = re.match(r"^([^：]{1,24})：\s*(.+)$", value)
    if not match:
        return value
    prefix, body = match.groups()
    if re.search(r"[\u3040-\u30ff]", prefix):
        return body
    return value


def yomitan_reference_info(tags: list[str], definitions: list[str], markers: list[str]) -> dict[str, Any]:
    if "non-lemma" not in set(tags):
        return {}
    targets = [
        definition
        for definition in definitions
        if definition not in {"alt-of", "alternative kanji"}
    ]
    if not targets:
        return {}
    reference_type = "spelling" if "alternative kanji" in set(markers) else "see_also"
    return {"type": reference_type, "targets": unique_strings(targets)}


def is_yomitan_redirect_reference(tags: list[str], definitions: list[str], markers: list[str]) -> bool:
    return "non-lemma" in set(tags) and any(
        "redirected from" in value for value in [*definitions, *markers]
    )


def _flatten_yomitan_glossary(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = normalize_space(value)
        return [text] if text else []
    if isinstance(value, int | float | bool):
        return [str(value)]
    if isinstance(value, list):
        results: list[str] = []
        for item in value:
            results.extend(_flatten_yomitan_glossary(item))
        return results
    if isinstance(value, dict):
        results: list[str] = []
        for key in ("text", "content", "children"):
            if key in value:
                results.extend(_flatten_yomitan_glossary(value[key]))
        return results
    return []


def split_tags(value: Any) -> list[str]:
    if isinstance(value, list):
        return unique_strings(str(item).strip() for item in value)
    return unique_strings(re.split(r"[\s,;]+", str(value or "").strip()))


def normalize_dictionary_text(value: Any) -> str:
    return unicodedata.normalize("NFC", str(value or "")).strip()


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(value or ""))).strip()


def strip_html_to_text(value: Any) -> str:
    text = value.decode("utf-8", errors="replace") if isinstance(value, bytes) else str(value or "")
    parser = _HTMLTextExtractor()
    parser.feed(text)
    parser.close()
    lines = [normalize_space(line) for line in "".join(parser.parts).splitlines()]
    return "\n".join(line for line in lines if line)


class _HTMLTextExtractor(HTMLParser):
    block_tags = {"br", "div", "p", "li", "tr", "table", "section", "article", "h1", "h2", "h3", "h4"}

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in self.block_tags:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self.block_tags:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if data:
            self.parts.append(data)


def truncate_text(value: str, limit: int) -> str:
    text = value.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def import_mdx_class() -> Any:
    try:
        ensure_mdict_lzo_support()
        from mdict_utils.reader import MDX
    except Exception as exc:  # pragma: no cover - dependency error message path
        raise DictionaryImportError(f"MDX support is unavailable: {exc}") from exc
    return MDX


def read_mdx_record(mdx: Any, *, key: bytes, offset: int, length: int) -> Any:
    try:
        ensure_mdict_lzo_support()
        from mdict_utils.reader import get_record
    except Exception as exc:  # pragma: no cover - dependency error message path
        raise DictionaryImportError(f"MDX support is unavailable: {exc}") from exc
    return get_record(mdx, key, offset, length)


def ensure_mdict_lzo_support() -> None:
    try:
        import lzo  # noqa: F401
    except ImportError:
        try:
            from mdict_utils.base import lzo as pure_lzo
            from mdict_utils.base import readmdict
        except Exception as exc:  # pragma: no cover - dependency error message path
            raise DictionaryImportError(f"MDX LZO support is unavailable: {exc}") from exc
        readmdict.lzo = _MdictLzoAdapter(pure_lzo)


class _MdictLzoAdapter:
    def __init__(self, pure_lzo: Any) -> None:
        self._pure_lzo = pure_lzo

    def decompress(self, data: bytes, initSize: int = 16000, blockSize: int = 8192) -> bytes:  # noqa: N803
        if data.startswith(b"\xf0") and len(data) >= 5:
            initSize = struct.unpack(">I", data[1:5])[0]
            data = data[5:]
        return self._pure_lzo.decompress(data, initSize=initSize, blockSize=blockSize)


def cached_mdx(source_path: Path) -> Any:
    mtime = source_path.stat().st_mtime
    cache_key = (str(source_path), mtime)
    cached = _MDX_CACHE.get(cache_key)
    if cached is not None:
        return cached
    MDX = import_mdx_class()
    mdx = MDX(str(source_path))
    _MDX_CACHE.clear()
    _MDX_CACHE[cache_key] = mdx
    return mdx


def decode_mdx_key(value: Any) -> str:
    if isinstance(value, bytes):
        return normalize_dictionary_text(value.decode("utf-8", errors="replace").strip("\x00"))
    return normalize_dictionary_text(value)


def unique_dictionary_id(title: str, content_hash: str, registry: dict[str, Any]) -> str:
    base = safe_slug(title) or "dictionary"
    suffix = content_hash[:10]
    candidate = f"{base}-{suffix}"
    used = {record.get("id") for record in registry.get("dictionaries", [])}
    if candidate not in used:
        return candidate
    index = 2
    while f"{candidate}-{index}" in used:
        index += 1
    return f"{candidate}-{index}"


def safe_slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or "")).strip().lower()
    slug = re.sub(r"[^0-9a-zA-Z\u3040-\u30ff\u3400-\u9fff々〆]+", "-", normalized).strip("-")
    return slug[:60] or "dictionary"


def next_dictionary_priority(registry: dict[str, Any]) -> int:
    priorities = [int(record.get("priority") or 0) for record in registry.get("dictionaries", [])]
    return (max(priorities) + 100) if priorities else 100


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_stream_with_hash(stream: BinaryIO, destination: Path) -> str:
    ensure_dir(destination.parent)
    digest = hashlib.sha256()
    with destination.open("wb") as output:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            if not chunk:
                break
            digest.update(chunk)
            output.write(chunk)
    return digest.hexdigest()


def replace_file(source: Path, destination: Path) -> None:
    try:
        source.replace(destination)
    except OSError:
        shutil.move(str(source), str(destination))


def unique_strings(values: Iterable[Any]) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []
    for value in values:
        text = normalize_dictionary_text(value)
        if not text or text in seen:
            continue
        seen.add(text)
        results.append(text)
    return results


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
