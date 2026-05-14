from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .corpus_export import (
    analysis_to_dict,
    corpus_index_path,
    corpus_source_details_dir,
    corpus_word_details_dir,
    source_detail_path,
    source_index_entry_from_detail,
    source_document_key,
    word_detail_path,
    word_index_entry_from_detail,
    write_corpus_detail_json,
    write_corpus_index_json,
    write_json_file,
)
from .jlpt import load_jlpt_words
from .paths import DEFAULT_JLPT_WORDS, DEFAULT_ZH_DICT, ensure_parent
from .texts import normalize_display_text, text_file_from_path
from .zh_dict import ChineseGlossary


DEFAULT_WEB_TEXT_DIR = Path("texts") / "web"
MAX_IMPORTED_TEXT_CHARS = 1_500_000


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def import_text_document(raw: dict[str, Any], *, directory: Path = DEFAULT_WEB_TEXT_DIR) -> dict[str, Any]:
    text = clean_imported_text(raw.get("text"))
    if not text:
        raise ValueError("Imported text is empty.")
    if len(text) > MAX_IMPORTED_TEXT_CHARS:
        raise ValueError(f"Imported text is too long. Limit: {MAX_IMPORTED_TEXT_CHARS} characters.")
    title = normalize_display_text(raw.get("title") or "") or "Imported web text"
    url = text_limit(raw.get("url"), 2000)
    content_sha256 = imported_text_hash(text)
    directory.mkdir(parents=True, exist_ok=True)
    duplicate = find_duplicate_import(content_sha256, directory=directory)
    if duplicate:
        return duplicate
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = unique_import_path(directory / f"{timestamp}-{slugify_import_title(title)}.txt")
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    metadata = {
        "source": "web",
        "title": title,
        "url": url,
        "imported_at": _now_iso(),
        "characters": len(text),
        "content_sha256": content_sha256,
    }
    metadata_path = path.with_name(f"{path.stem}.meta.json")
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "title": title,
        "path": str(path),
        "metadata_path": str(metadata_path),
        "characters": len(text),
        "url": url,
        "content_sha256": content_sha256,
        "duplicate": False,
    }


def imported_text_hash(text: str) -> str:
    return hashlib.sha256(text.rstrip().encode("utf-8")).hexdigest()


def find_duplicate_import(content_sha256: str, *, directory: Path = DEFAULT_WEB_TEXT_DIR) -> dict[str, Any] | None:
    if not directory.exists():
        return None
    for path in sorted(directory.glob("*.txt")):
        metadata_path = path.with_name(f"{path.stem}.meta.json")
        metadata = read_import_metadata(metadata_path)
        existing_hash = metadata.get("content_sha256") or imported_text_hash(
            clean_imported_text(path.read_text(encoding="utf-8", errors="replace"))
        )
        if existing_hash != content_sha256:
            continue
        return {
            "title": normalize_display_text(metadata.get("title") or path.stem),
            "path": str(path),
            "metadata_path": str(metadata_path),
            "characters": int(metadata.get("characters") or path.stat().st_size),
            "url": text_limit(metadata.get("url"), 2000),
            "content_sha256": content_sha256,
            "duplicate": True,
        }
    return None


def read_import_metadata(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def delete_imported_text_documents(raw: dict[str, Any], *, directory: Path = DEFAULT_WEB_TEXT_DIR) -> dict[str, Any]:
    raw_files = raw.get("source_files")
    if raw_files is None:
        raw_files = [raw.get("source_file")]
    if not isinstance(raw_files, list):
        raise ValueError("source_files must be a list.")
    source_files = [str(item or "").strip() for item in raw_files if str(item or "").strip()]
    if not source_files:
        raise ValueError("No imported text file was specified.")

    deleted: list[dict[str, Any]] = []
    missing: list[str] = []
    for source_file in source_files:
        path = resolve_imported_text_path(source_file, directory=directory)
        metadata_path = path.with_name(f"{path.stem}.meta.json")
        existed = path.exists() or metadata_path.exists()
        if not existed:
            missing.append(source_file)
            continue
        path.unlink(missing_ok=True)
        metadata_path.unlink(missing_ok=True)
        deleted.append({
            "source_file": source_file,
            "path": str(path),
            "metadata_path": str(metadata_path),
        })

    return {
        "deleted": deleted,
        "missing": missing,
    }


def resolve_imported_text_path(source_file: str, *, directory: Path = DEFAULT_WEB_TEXT_DIR) -> Path:
    if "\x00" in source_file:
        raise ValueError("Invalid imported text path.")
    raw_path = Path(source_file)
    if raw_path.is_absolute():
        candidate = raw_path
    elif raw_path.parts and raw_path.parts[0] == directory.name:
        candidate = directory.parent / raw_path
    else:
        candidate = directory / raw_path

    root = directory.resolve()
    path = candidate.resolve()
    if path.suffix != ".txt" or root not in path.parents:
        raise ValueError("Only imported web text files can be deleted.")
    return path


def clean_imported_text(value: Any) -> str:
    text = normalize_display_text_preserving_lines(value)
    lines = [re.sub(r"[ \t　]+", " ", line).strip() for line in text.splitlines()]
    cleaned_lines: list[str] = []
    previous_blank = False
    for line in lines:
        blank = not line
        if blank and previous_blank:
            continue
        cleaned_lines.append(line)
        previous_blank = blank
    return "\n".join(cleaned_lines).strip()


def normalize_display_text_preserving_lines(value: Any) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    return unicodedata.normalize("NFC", text)


def slugify_import_title(title: str) -> str:
    slug = re.sub(r"[^\w\u3040-\u30ff\u3400-\u9fff]+", "-", title, flags=re.UNICODE)
    slug = slug.strip("-_")
    return (slug[:80].strip("-_") or "web-text")


def unique_import_path(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(2, 1000):
        candidate = path.with_name(f"{path.stem}-{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not find an available import path for {path}")


def refresh_imported_texts_corpus(
    *,
    corpus_path: Path,
    directory: Path = DEFAULT_WEB_TEXT_DIR,
) -> dict[str, Any]:
    if split_corpus_available(corpus_path):
        return refresh_imported_texts_split(corpus_path=corpus_path, directory=directory)
    payload = json.loads(corpus_path.read_text(encoding="utf-8"))
    old_files = {
        str(source.get("source_file") or "")
        for source in as_dict_list(payload.get("sources"))
        if is_imported_text_source(source)
    }
    current_paths = sorted(directory.glob("*.txt")) if directory.exists() else []
    current_files_by_path = {
        path: text_file_from_path(path, root=directory.parent).name
        for path in current_paths
    }
    new_paths = [
        path
        for path, source_file in current_files_by_path.items()
        if source_file not in old_files
    ]
    web_payload = imported_texts_payload(directory=directory, paths=new_paths)
    merged, stats = merge_imported_text_payload(
        payload,
        web_payload,
        current_imported_files=set(current_files_by_path.values()),
    )
    ensure_parent(corpus_path)
    corpus_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_corpus_detail_json(merged, corpus_path)
    write_corpus_index_json(merged, corpus_index_path(corpus_path))
    return {
        "output": str(corpus_path),
        **stats,
    }


def split_corpus_available(corpus_path: Path) -> bool:
    resolved = corpus_path.resolve()
    return (
        corpus_index_path(resolved).exists()
        and corpus_word_details_dir(resolved).is_dir()
        and corpus_source_details_dir(resolved).is_dir()
    )


def refresh_imported_texts_split(
    *,
    corpus_path: Path,
    directory: Path = DEFAULT_WEB_TEXT_DIR,
) -> dict[str, Any]:
    resolved = corpus_path.resolve()
    index_path = corpus_index_path(resolved)
    index_payload = json.loads(index_path.read_text(encoding="utf-8"))
    old_sources = [
        source
        for source in as_dict_list(index_payload.get("sources"))
        if is_imported_text_source(source)
    ]
    old_files = {str(source.get("source_file") or "") for source in old_sources}
    current_paths = sorted(directory.glob("*.txt")) if directory.exists() else []
    current_files_by_path = {
        path: text_file_from_path(path, root=directory.parent).name
        for path in current_paths
    }
    current_files = set(current_files_by_path.values())
    new_paths = [
        path
        for path, source_file in current_files_by_path.items()
        if source_file not in old_files
    ]
    removed_source_details = [
        source
        for source in (
            load_split_source_detail(resolved, str(source.get("source_key") or ""))
            for source in old_sources
            if str(source.get("source_file") or "") not in current_files
        )
        if source
    ]
    web_payload = imported_texts_payload(directory=directory, paths=new_paths)
    new_sources = [
        source
        for source in as_dict_list(web_payload.get("sources"))
        if is_imported_text_source(source)
    ]
    new_words = {
        str(word.get("word") or ""): word
        for word in active_imported_words(web_payload)
        if word.get("word")
    }
    removed_contributions = imported_source_contributions(removed_source_details)
    words_by_key = {
        str(word.get("word")): word
        for word in as_dict_list(index_payload.get("words"))
        if word.get("word")
    }
    affected_words = set(removed_contributions) | set(new_words)
    for word_text in affected_words:
        detail = load_split_word_detail(resolved, word_text) or words_by_key.get(word_text) or {"word": word_text}
        if word_text in removed_contributions:
            subtract_imported_word_contribution(detail, removed_contributions[word_text])
        if word_text in new_words:
            merge_imported_word(detail, new_words[word_text])
        if removable_zero_candidate(detail):
            word_detail_path(resolved, word_text).unlink(missing_ok=True)
            words_by_key.pop(word_text, None)
            continue
        write_json_file(word_detail_path(resolved, word_text), detail)
        words_by_key[word_text] = word_index_entry_from_detail(detail)

    removed_keys = {
        str(source.get("source_key") or "")
        for source in old_sources
        if str(source.get("source_file") or "") not in current_files
    }
    for key in removed_keys:
        if key:
            source_detail_path(resolved, key).unlink(missing_ok=True)
    for source in new_sources:
        key = str(source.get("source_key") or source_document_key(source))
        source["source_key"] = key
        write_json_file(source_detail_path(resolved, key), source)

    kept_sources = [
        source
        for source in old_sources
        if str(source.get("source_file") or "") in current_files
    ]
    index_payload["sources"] = [
        source
        for source in as_dict_list(index_payload.get("sources"))
        if not is_imported_text_source(source)
    ] + kept_sources + [source_index_entry_from_detail(source) for source in new_sources]
    index_payload["words"] = sorted(words_by_key.values(), key=word_payload_sort_key)
    update_imported_text_summary(index_payload, web_payload, removed_source_details, new_sources)
    update_imported_text_shows(index_payload, web_payload, removed_source_details)
    index_payload["generated_at"] = datetime.now().isoformat(timespec="seconds")
    write_json_file(index_path, index_payload)
    current_sources = kept_sources + [source_index_entry_from_detail(source) for source in new_sources]
    return {
        "output": str(index_path),
        "split_output": True,
        "old_imported_text_count": len(old_sources),
        "imported_text_count": len(current_sources),
        "imported_text_token_count": sum_source_tokens(current_sources),
        "refreshed_imported_text_count": len(new_sources),
        "removed_imported_text_count": len(removed_source_details),
    }


def load_split_word_detail(corpus_path: Path, word_text: str) -> dict[str, Any] | None:
    return read_json_dict(word_detail_path(corpus_path, word_text))


def load_split_source_detail(corpus_path: Path, source_key: str) -> dict[str, Any] | None:
    return read_json_dict(source_detail_path(corpus_path, source_key))


def read_json_dict(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def imported_texts_payload(
    *,
    directory: Path = DEFAULT_WEB_TEXT_DIR,
    paths: list[Path] | None = None,
) -> dict[str, Any]:
    from .analysis import analyze_media

    web_paths = paths if paths is not None else sorted(directory.glob("*.txt")) if directory.exists() else []
    text_files = [text_file_from_path(path, root=directory.parent) for path in web_paths]
    analysis = analyze_media(
        watched_show_count=0,
        music_track_count=0,
        subtitle_files=[],
        lyric_files=[],
        text_files=text_files,
        jlpt_words=load_jlpt_words(DEFAULT_JLPT_WORDS),
        max_examples_per_word=60,
        context_lines=2,
        context_min_chars=40,
        context_max_lines=4,
    )
    return analysis_to_dict(
        analysis,
        examples_per_word=5,
        zh_glossary=ChineseGlossary.load(DEFAULT_ZH_DICT),
        include_zero_count_words=False,
    )


def merge_imported_text_payload(
    payload: dict[str, Any],
    web_payload: dict[str, Any],
    *,
    current_imported_files: set[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    merged = json.loads(json.dumps(payload, ensure_ascii=False))
    old_sources = [
        source
        for source in as_dict_list(merged.get("sources"))
        if is_imported_text_source(source)
    ]
    if current_imported_files is None:
        current_imported_files = {
            str(source.get("source_file") or "")
            for source in as_dict_list(web_payload.get("sources"))
            if is_imported_text_source(source)
        }
    removed_sources = [
        source
        for source in old_sources
        if str(source.get("source_file") or "") not in current_imported_files
    ]
    kept_sources = [
        source
        for source in old_sources
        if str(source.get("source_file") or "") in current_imported_files
    ]
    new_sources = [
        source
        for source in as_dict_list(web_payload.get("sources"))
        if is_imported_text_source(source)
    ]
    old_contributions = imported_source_contributions(removed_sources)
    words_by_key = {
        str(word.get("word")): word
        for word in as_dict_list(merged.get("words"))
        if word.get("word")
    }
    for word_text, contribution in old_contributions.items():
        word = words_by_key.get(word_text)
        if word:
            subtract_imported_word_contribution(word, contribution)

    for word_text in list(words_by_key):
        if removable_zero_candidate(words_by_key[word_text]):
            del words_by_key[word_text]

    for web_word in active_imported_words(web_payload):
        word_text = str(web_word.get("word") or "")
        if not word_text:
            continue
        existing = words_by_key.get(word_text)
        if existing:
            merge_imported_word(existing, web_word)
        else:
            words_by_key[word_text] = json.loads(json.dumps(web_word, ensure_ascii=False))

    merged["sources"] = [
        source
        for source in as_dict_list(merged.get("sources"))
        if not is_imported_text_source(source)
    ] + kept_sources + new_sources
    merged["words"] = sorted(words_by_key.values(), key=word_payload_sort_key)
    update_imported_text_summary(merged, web_payload, removed_sources, new_sources)
    update_imported_text_shows(merged, web_payload, removed_sources)
    merged["generated_at"] = datetime.now().isoformat(timespec="seconds")
    current_sources = kept_sources + new_sources
    return merged, {
        "old_imported_text_count": len(old_sources),
        "imported_text_count": len(current_sources),
        "imported_text_token_count": sum_source_tokens(current_sources),
        "refreshed_imported_text_count": len(new_sources),
        "removed_imported_text_count": len(removed_sources),
    }


def as_dict_list(value: Any) -> list[dict[str, Any]]:
    return [item for item in value or [] if isinstance(item, dict)]


def is_imported_text_source(source: dict[str, Any]) -> bool:
    source_file = str(source.get("source_file") or source.get("subtitle_file") or "")
    return source.get("source_type") == "text" and source_file.startswith("web/") and source_file.endswith(".txt")


def imported_source_contributions(sources: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    contributions: dict[str, dict[str, Any]] = {}
    for source in sources:
        title = str(source.get("source_title") or "")
        source_file = str(source.get("source_file") or "")
        for line in as_dict_list(source.get("lines")):
            for match in as_dict_list(line.get("matches")):
                word = str(match.get("word") or "")
                if not word:
                    continue
                contribution = contributions.setdefault(
                    word,
                    {
                        "count": 0,
                        "sources": Counter(),
                        "files": set(),
                    },
                )
                contribution["count"] += 1
                if title:
                    contribution["sources"][title] += 1
                if source_file:
                    contribution["files"].add(source_file)
    return contributions


def subtract_imported_word_contribution(word: dict[str, Any], contribution: dict[str, Any]) -> None:
    count = int(contribution.get("count") or 0)
    word["count"] = max(int(word.get("count") or 0) - count, 0)
    source_type_counts = dict(word.get("source_type_counts") or {})
    source_type_counts["text"] = max(int(source_type_counts.get("text") or 0) - count, 0)
    if source_type_counts["text"] <= 0:
        source_type_counts.pop("text", None)
    word["source_type_counts"] = source_type_counts
    sync_word_source_count_fields(word)
    subtract_word_sources(word, contribution.get("sources") or Counter())
    files = set(contribution.get("files") or [])
    word["examples"] = [
        example
        for example in as_dict_list(word.get("examples"))
        if example_source_file(example) not in files
    ]


def subtract_word_sources(word: dict[str, Any], counts: Counter[str]) -> None:
    if not counts:
        return
    source_counts = Counter()
    for source in as_dict_list(word.get("sources")):
        title = str(source.get("title") or "")
        if title:
            source_counts[title] += int(source.get("count") or 0)
    source_counts.subtract(counts)
    word["sources"] = [
        {"title": title, "count": count}
        for title, count in source_counts.items()
        if count > 0
    ]


def active_imported_words(web_payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        word
        for word in as_dict_list(web_payload.get("words"))
        if imported_word_count(word) > 0
    ]


def imported_word_count(word: dict[str, Any]) -> int:
    counts = word.get("source_type_counts") or {}
    return int(word.get("text_count") or counts.get("text") or 0)


def merge_imported_word(target: dict[str, Any], source: dict[str, Any]) -> None:
    count = imported_word_count(source)
    target["count"] = int(target.get("count") or 0) + count
    source_type_counts = dict(target.get("source_type_counts") or {})
    source_type_counts["text"] = int(source_type_counts.get("text") or 0) + count
    target["source_type_counts"] = source_type_counts
    sync_word_source_count_fields(target)
    merge_word_sources(target, as_dict_list(source.get("sources")))
    merge_word_examples(target, as_dict_list(source.get("examples")))
    for key in ("reading", "level", "level_number", "meaning", "meaning_zh", "lexical_notes"):
        if not target.get(key) and source.get(key):
            target[key] = source[key]


def merge_word_sources(target: dict[str, Any], source_items: list[dict[str, Any]]) -> None:
    counts = Counter()
    for source in as_dict_list(target.get("sources")):
        title = str(source.get("title") or "")
        if title:
            counts[title] += int(source.get("count") or 0)
    for source in source_items:
        title = str(source.get("title") or "")
        if title:
            counts[title] += int(source.get("count") or 0)
    target["sources"] = [
        {"title": title, "count": count}
        for title, count in counts.most_common()
        if count > 0
    ]


def merge_word_examples(target: dict[str, Any], source_examples: list[dict[str, Any]]) -> None:
    examples = as_dict_list(target.get("examples"))
    seen = {example_key(example) for example in examples}
    for example in source_examples:
        key = example_key(example)
        if key in seen:
            continue
        seen.add(key)
        examples.append(example)
    target["examples"] = examples


def sync_word_source_count_fields(word: dict[str, Any]) -> None:
    counts = dict(word.get("source_type_counts") or {})
    word["subtitle_count"] = int(counts.get("subtitle") or 0)
    word["lyrics_count"] = int(counts.get("lyrics") or 0)
    word["text_count"] = int(counts.get("text") or 0)
    if counts:
        word["count"] = sum(int(value or 0) for value in counts.values())


def removable_zero_candidate(word: dict[str, Any]) -> bool:
    return (
        not word.get("level_number")
        and int(word.get("count") or 0) <= 0
        and not as_dict_list(word.get("examples"))
        and not as_dict_list(word.get("sources"))
    )


def example_key(example: dict[str, Any]) -> tuple[str, str, str]:
    return (
        re.sub(r"\s+", "", str(example.get("sentence") or "")),
        example_source_file(example),
        str(example.get("matched_text") or ""),
    )


def example_source_file(example: dict[str, Any]) -> str:
    reference = example.get("reference") if isinstance(example.get("reference"), dict) else {}
    return str(reference.get("source_file") or example.get("subtitle_file") or "")


def word_payload_sort_key(word: dict[str, Any]) -> tuple[int, int, str]:
    level = word.get("level_number")
    try:
        level_sort = int(level) if level else 9
    except (TypeError, ValueError):
        level_sort = 9
    return (-int(word.get("count") or 0), level_sort, str(word.get("word") or ""))


def update_imported_text_summary(
    merged: dict[str, Any],
    web_payload: dict[str, Any],
    old_sources: list[dict[str, Any]],
    new_sources: list[dict[str, Any]],
) -> None:
    summary = dict(merged.get("summary") or {})
    old_tokens = sum_source_tokens(old_sources)
    new_tokens = sum_source_tokens(new_sources)
    token_delta = new_tokens - old_tokens
    summary["text_file_count"] = max(int(summary.get("text_file_count") or 0) - len(old_sources) + len(new_sources), 0)
    summary["total_tokens"] = max(int(summary.get("total_tokens") or 0) + token_delta, 0)
    source_type_counts = dict(summary.get("source_type_counts") or {})
    source_type_counts["text"] = max(int(source_type_counts.get("text") or 0) + token_delta, 0)
    if source_type_counts["text"] <= 0:
        source_type_counts.pop("text", None)
    summary["source_type_counts"] = source_type_counts
    coverage = dict(summary.get("word_source_coverage") or {})
    words = as_dict_list(merged.get("words"))
    coverage["exported_word_count"] = len(words)
    if any(isinstance(word.get("lexical_notes"), dict) for word in words):
        coverage["exported_jmdict_word_count"] = sum(
            1
            for word in words
            if isinstance(word.get("lexical_notes"), dict) and word["lexical_notes"].get("senses")
        )
    coverage["exported_zh_meaning_word_count"] = sum(1 for word in words if word.get("meaning_zh"))
    coverage["exported_english_only_word_count"] = sum(
        1
        for word in words
        if word.get("meaning") and not word.get("meaning_zh")
    )
    summary["word_source_coverage"] = coverage
    web_summary = web_payload.get("summary") if isinstance(web_payload.get("summary"), dict) else {}
    if web_summary.get("unique_token_count") and not summary.get("unique_token_count"):
        summary["unique_token_count"] = web_summary["unique_token_count"]
    merged["summary"] = summary


def update_imported_text_shows(
    merged: dict[str, Any],
    web_payload: dict[str, Any],
    old_sources: list[dict[str, Any]],
) -> None:
    old_titles = {
        normalize_display_text(source.get("source_title") or "")
        for source in old_sources
        if source.get("source_title")
    }
    shows_by_title = {}
    for show in as_dict_list(merged.get("shows")):
        title = normalize_display_text(show.get("title") or "")
        if title and title not in old_titles:
            shows_by_title[title] = show
    for show in as_dict_list(web_payload.get("shows")):
        title = normalize_display_text(show.get("title") or "")
        if title:
            shows_by_title[title] = show
    merged["shows"] = sorted(shows_by_title.values(), key=lambda item: str(item.get("title") or ""))


def sum_source_tokens(sources: list[dict[str, Any]]) -> int:
    return sum(int(source.get("token_count") or 0) for source in sources)


def text_limit(value: Any, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."
