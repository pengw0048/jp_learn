from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import unicodedata
import uuid
from collections import Counter
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any

from .corpus_export import (
    INDEX_SCHEMA_VERSION,
    analysis_to_dict,
    corpus_index_from_payload,
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
from .jlpt import JLPTWords, load_jlpt_words
from .models import WordEntry
from .paths import (
    DEFAULT_JLPT_WORDS,
    DEFAULT_STATE_DB,
    DEFAULT_ZH_DICT,
    ensure_parent,
)
from .texts import normalize_display_text, text_file_from_path
from .tokenize import JapaneseTokenizer
from .viewer_config import (
    ALLOWED_PROVIDERS,
    llm_config_status,
    resolve_llm_client,
    viewer_config_status,
)
from .viewer_study import (
    clamp_study_count,
    study_status_for_word,
    viewer_study_state,
)
from .zh_dict import ChineseGlossary


ALLOWED_MAINTENANCE_TASKS = {
    "sync_media",
    "refresh_all",
    "sync_anime",
    "sync_music",
    "fetch_lyrics",
    "export_corpus",
    "refresh_imported_texts",
    "fetch_anime_db",
    "fetch_zh_dict",
    "fetch_jlpt_words",
    "fetch_jmdict",
    "fetch_kanjidic2",
    "fetch_lexical_resources",
}
CORPUS_RELOAD_TASKS = {"export_corpus", "refresh_imported_texts"}
DEFAULT_WEB_TEXT_DIR = Path("texts") / "web"
MAX_IMPORTED_TEXT_CHARS = 1_500_000
MAX_ANNOTATION_BLOCKS = 260
MAX_ANNOTATION_TEXT_CHARS = 48_000
MAX_ANNOTATIONS = 1_400
ANNOTATION_EXCLUDED_POS = {"助詞", "助動詞", "補助記号", "記号", "空白"}
NAME_TITLE_SURFACES = {
    "大統領",
    "国家主席",
    "主席",
    "首相",
    "氏",
    "さん",
    "君",
    "ちゃん",
    "先生",
    "選手",
    "監督",
    "社長",
    "教授",
    "容疑者",
}
KANJI_RE = re.compile(r"[\u3400-\u9fff々〆]")
JAPANESE_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff々〆ヵヶー]")
KATAKANA_RE = re.compile(r"[\u30a1-\u30f6]")
_ANNOTATION_INDEX_CACHE: dict[tuple[str, float], "AnnotationIndex"] = {}
_CORPUS_PAYLOAD_CACHE: dict[tuple[str, float], dict[str, Any]] = {}
_CORPUS_INDEX_CACHE: dict[tuple[str, float, float], dict[str, Any]] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ViewerJob:
    id: str
    kind: str
    status: str = "running"
    started_at: str = field(default_factory=_now_iso)
    finished_at: str | None = None
    spec: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)
    progress: dict[str, Any] = field(default_factory=dict)
    log: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "spec": self.spec,
            "result": self.result,
            "progress": self.progress,
            "log": self.log[-200:],
            "error": self.error,
        }


@dataclass(frozen=True)
class AnnotationIndex:
    words_by_surface: dict[str, dict[str, Any]]
    jlpt_words: JLPTWords | None
    zh_glossary: ChineseGlossary


class ViewerJobRunner:
    def __init__(self, *, corpus_path: Path, state_db: Path = DEFAULT_STATE_DB) -> None:
        self.corpus_path = corpus_path
        self.state_db = state_db
        self._lock = threading.Lock()
        self._job: ViewerJob | None = None

    def current_job(self) -> dict[str, Any] | None:
        with self._lock:
            return self._job.to_dict() if self._job else None

    def start_maintenance(self, raw_spec: dict[str, Any]) -> dict[str, Any]:
        spec = normalize_maintenance_spec(raw_spec)
        with self._lock:
            if self._job and self._job.status == "running":
                raise RuntimeError("Another maintenance job is already running.")
            job = ViewerJob(id=str(uuid.uuid4()), kind=spec["type"], spec=public_maintenance_spec(spec))
            self._job = job
        thread = threading.Thread(target=self._run_maintenance_job, args=(job, spec), daemon=True)
        thread.start()
        return job.to_dict()

    def _run_maintenance_job(self, job: ViewerJob, spec: dict[str, Any]) -> None:
        try:
            if spec["type"] in {"sync_media", "refresh_all"}:
                result = self._run_composite_job(job, spec)
            elif spec["type"] == "export_corpus":
                result = self._run_export_corpus(job)
            elif spec["type"] == "refresh_imported_texts":
                result = self._run_refresh_imported_texts(job)
            else:
                result = self._run_maintenance_task(job, spec)
                result["reload_corpus"] = spec["type"] in CORPUS_RELOAD_TASKS
            self._finish(job, "succeeded", result)
        except Exception as exc:
            self._log(job, f"Job failed: {exc}")
            self._finish(job, "failed", {}, error=str(exc))

    def _run_composite_job(self, job: ViewerJob, spec: dict[str, Any]) -> dict[str, Any]:
        steps = composite_maintenance_steps(spec)
        completed_steps = []
        result: dict[str, Any] = {"steps": completed_steps, "reload_corpus": True}
        self._set_progress(
            job,
            {
                "phase": "steps",
                "total": len(steps),
                "completed": 0,
                "current_step": None,
                "percent": 0.0,
            },
        )
        for index, (label, step_spec) in enumerate(steps, start=1):
            self._set_progress(
                job,
                {
                    "phase": "steps",
                    "total": len(steps),
                    "completed": index - 1,
                    "current_step": label,
                    "percent": round(((index - 1) / len(steps)) * 100, 1),
                },
            )
            self._log(job, f"Step {index}/{len(steps)}: {label}")
            if step_spec["type"] == "export_corpus":
                step_result = self._run_export_corpus(job)
            else:
                step_result = self._run_maintenance_task(job, step_spec)
            completed_steps.append(
                {
                    "type": step_spec["type"],
                    "label": label,
                    "result": step_result,
                }
            )
            self._set_progress(
                job,
                {
                    "phase": "steps",
                    "total": len(steps),
                    "completed": index,
                    "current_step": label,
                    "percent": round((index / len(steps)) * 100, 1),
                },
            )
        return result

    def _run_export_corpus(self, job: ViewerJob) -> dict[str, Any]:
        if not job.progress:
            self._set_progress(
                job,
                {
                    "phase": "export",
                    "total": 1,
                    "completed": 0,
                    "current_step": "Export corpus",
                    "percent": 0.0,
                },
            )
        raw_path = Path("corpus.json")
        self._run_export_corpus_file(job, raw_path)
        served_path = self.corpus_path.resolve()
        if job.kind == "export_corpus":
            self._set_progress(
                job,
                {
                    "phase": "export",
                    "total": 1,
                    "completed": 1,
                    "current_step": "Export corpus",
                    "percent": 100.0,
                },
            )
        if served_path == raw_path.resolve():
            return {"output": str(raw_path), "reload_corpus": True}
        self._log(job, f"Copying exported corpus to served path: {served_path}")
        ensure_parent(served_path)
        served_path.write_bytes(raw_path.read_bytes())
        return {
            "output": str(served_path),
            "raw_output": str(raw_path),
            "reload_corpus": True,
        }

    def _run_refresh_imported_texts(self, job: ViewerJob) -> dict[str, Any]:
        if not job.progress:
            self._set_progress(
                job,
                {
                    "phase": "export",
                    "total": 1,
                    "completed": 0,
                    "current_step": "Refresh imported texts",
                    "percent": 0.0,
                },
            )
        raw_path = Path("corpus.json")
        base_path = raw_path if raw_path.exists() else self.corpus_path
        if not base_path.exists():
            self._log(job, "No existing corpus found; falling back to full export.")
            return self._run_export_corpus(job)

        result = self._run_callable(
            job,
            "Refresh imported texts",
            refresh_imported_texts_corpus,
            corpus_path=base_path,
        )
        served_path = self.corpus_path.resolve()
        if served_path != base_path.resolve():
            self._log(job, f"Copying refreshed corpus to served path: {served_path}")
            ensure_parent(served_path)
            served_path.write_bytes(base_path.read_bytes())
            index_path = corpus_index_path(base_path)
            if index_path.exists():
                corpus_index_path(served_path).write_bytes(index_path.read_bytes())
            result["output"] = str(served_path)
            result["raw_output"] = str(base_path)
        if job.kind == "refresh_imported_texts":
            self._set_progress(
                job,
                {
                    "phase": "export",
                    "total": 1,
                    "completed": 1,
                    "current_step": "Refresh imported texts",
                    "percent": 100.0,
                },
            )
        result["reload_corpus"] = True
        return result

    def _run_export_corpus_file(self, job: ViewerJob, output: Path) -> dict[str, Any]:
        from . import tasks

        return self._run_callable(
            job,
            "Export corpus",
            tasks.export_corpus_json,
            output=output,
            state_db=self.state_db,
            jlpt_words=tasks.DEFAULT_JLPT_WORDS,
            level=None,
            limit=None,
            examples_per_word=5,
            context_lines=2,
            context_min_chars=40,
            context_max_lines=4,
            zh_dict=tasks.DEFAULT_ZH_DICT,
            jmdict=tasks.DEFAULT_JMDICT,
            kanjidic2=tasks.DEFAULT_KANJIDIC2,
            lexical_notes=True,
            subtitles=None,
            texts=None,
            text_dir=tasks.DEFAULT_TEXTS_DIR,
        )

    def _run_maintenance_task(self, job: ViewerJob, spec: dict[str, Any]) -> dict[str, Any]:
        from . import tasks

        task_type = spec["type"]
        if task_type == "sync_anime":
            return self._run_callable(
                job,
                "Sync Bangumi anime and subtitles",
                tasks.sync,
                state_db=self.state_db,
                anime_db=tasks.DEFAULT_ANIME_DB,
                cache_dir=tasks.DEFAULT_JIMAKU_CACHE,
                max_shows=None,
                max_files_per_show=24,
                download_subtitles=True,
            )
        if task_type == "sync_music":
            return self._run_callable(
                job,
                "Sync Bangumi music tracks",
                tasks.sync_lyrics,
                state_db=self.state_db,
                max_albums=None,
                max_tracks=None,
            )
        if task_type == "fetch_lyrics":
            return self._run_callable(
                job,
                "Fetch missing LRCLIB lyrics",
                tasks.fetch_lyrics,
                state_db=self.state_db,
                cache_dir=tasks.DEFAULT_LYRICS_CACHE,
                limit=spec["limit"],
                overwrite=spec["overwrite"],
                force=False,
                concurrency=spec["concurrency"],
            )
        if task_type == "fetch_anime_db":
            return self._run_callable(
                job,
                "Update Anime Offline Database",
                tasks.fetch_anime_db,
                output=tasks.DEFAULT_ANIME_DB,
            )
        if task_type == "fetch_zh_dict":
            return self._run_callable(
                job,
                "Update Japanese-Chinese dictionary",
                tasks.fetch_zh_dict,
                output=tasks.DEFAULT_ZH_DICT,
                source_url="https://raw.githubusercontent.com/lxl66566/Japanese-Chinese-thesaurus/main/final.json",
            )
        if task_type == "fetch_jlpt_words":
            return self._run_callable(
                job,
                "Update JLPT word list",
                tasks.fetch_jlpt_words,
                output=tasks.DEFAULT_JLPT_WORDS,
                source_url="https://raw.githubusercontent.com/elzup/jlpt-word-list/master/out/all.csv",
            )
        if task_type == "fetch_jmdict":
            return self._run_callable(
                job,
                "Update JMdict",
                tasks.fetch_jmdict,
                output=tasks.DEFAULT_JMDICT,
                source_url="http://ftp.edrdg.org/pub/Nihongo/JMdict_e_examp.gz",
            )
        if task_type == "fetch_kanjidic2":
            return self._run_callable(
                job,
                "Update KANJIDIC2",
                tasks.fetch_kanjidic2,
                output=tasks.DEFAULT_KANJIDIC2,
                source_url="http://ftp.edrdg.org/pub/Nihongo/kanjidic2.xml.gz",
            )
        if task_type == "fetch_lexical_resources":
            return self._run_callable(
                job,
                "Update lexical resources",
                tasks.fetch_lexical_resources,
                jmdict_output=tasks.DEFAULT_JMDICT,
                kanjidic2_output=tasks.DEFAULT_KANJIDIC2,
            )
        raise ValueError(f"Unsupported maintenance task: {task_type}")

    def _run_callable(self, job: ViewerJob, label: str, func: Any, **kwargs: Any) -> dict[str, Any]:
        self._log(job, f"Running: {label}")
        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            func(**kwargs)
        for output in (stdout.getvalue(), stderr.getvalue()):
            for line in output.splitlines():
                if line:
                    self._log(job, line)
        return {"ok": True}

    def _log(self, job: ViewerJob, message: str) -> None:
        timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        with self._lock:
            job.log.append(f"{timestamp} {message}")

    def _set_progress(self, job: ViewerJob, progress: dict[str, Any]) -> None:
        with self._lock:
            job.progress = dict(progress)

    def _finish(
        self,
        job: ViewerJob,
        status: str,
        result: dict[str, Any],
        *,
        error: str | None = None,
    ) -> None:
        with self._lock:
            job.status = status
            job.finished_at = _now_iso()
            job.result = result
            job.error = error


def maintenance_status(runner: ViewerJobRunner | None) -> dict[str, Any]:
    return {
        "enabled": runner is not None,
        "corpus_path": str(runner.corpus_path) if runner else None,
        "tasks": sorted(ALLOWED_MAINTENANCE_TASKS),
        "llm": llm_config_status(),
        "config": viewer_config_status(),
        "job": runner.current_job() if runner else None,
    }


def explain_reader_usage(raw: dict[str, Any]) -> dict[str, Any]:
    word = raw.get("word")
    example = raw.get("example")
    if not isinstance(word, dict) or not isinstance(example, dict):
        raise ValueError("Explanation requires word and example objects.")
    question = text_limit(raw.get("question"), 500).strip()

    provider = str(raw.get("provider") or os.environ.get("JPCORPUS_LLM_PROVIDER") or "openai-compatible")
    if provider not in ALLOWED_PROVIDERS:
        raise ValueError(f"Unsupported provider: {provider}")
    client = resolve_llm_client(
        provider=provider,
        model=raw.get("model") or os.environ.get("JPCORPUS_LLM_MODEL") or os.environ.get("ANTHROPIC_MODEL"),
        use_show_context=False,
    )
    try:
        compact_word = compact_reader_word(word)
        compact_example = compact_reader_example(example)
        if question:
            answer_question = getattr(client, "answer_question", None)
            if not callable(answer_question):
                raise ValueError("Configured LLM does not support reader questions.")
            return {"answer": answer_question(compact_word, compact_example, question)}
        explanation = client.explain_example(compact_word, compact_example)
        return {"explanation": explanation}
    finally:
        close_client = getattr(client, "close", None)
        if callable(close_client):
            close_client()


def annotate_text_blocks(raw: dict[str, Any], *, corpus_path: Path) -> dict[str, Any]:
    raw_blocks = raw.get("blocks")
    if not isinstance(raw_blocks, list):
        raise ValueError("Annotation requires a blocks array.")

    blocks: list[dict[str, str]] = []
    total_chars = 0
    for index, item in enumerate(raw_blocks[:MAX_ANNOTATION_BLOCKS]):
        if not isinstance(item, dict):
            continue
        block_id = text_limit(item.get("id") if item.get("id") is not None else index, 80)
        text = unicodedata.normalize("NFC", str(item.get("text") or ""))
        if not block_id or not text or not JAPANESE_RE.search(text):
            continue
        remaining = MAX_ANNOTATION_TEXT_CHARS - total_chars
        if remaining <= 0:
            break
        if len(text) > remaining:
            text = text[:remaining]
        total_chars += len(text)
        blocks.append({"id": block_id, "text": text})

    index = load_annotation_index(corpus_path)
    study_state = viewer_study_state()
    tokenizer = JapaneseTokenizer()
    annotated_blocks = []
    total_annotations = 0
    for block in blocks:
        ranges = annotate_one_text_block(block["text"], tokenizer=tokenizer, index=index, study_state=study_state)
        if total_annotations + len(ranges) > MAX_ANNOTATIONS:
            ranges = ranges[: max(0, MAX_ANNOTATIONS - total_annotations)]
        total_annotations += len(ranges)
        annotated_blocks.append({"id": block["id"], "ranges": ranges})
        if total_annotations >= MAX_ANNOTATIONS:
            break

    return {
        "blocks": annotated_blocks,
        "stats": {
            "requested_blocks": len(raw_blocks),
            "annotated_blocks": len(annotated_blocks),
            "annotations": total_annotations,
            "truncated": len(raw_blocks) > len(blocks) or total_chars >= MAX_ANNOTATION_TEXT_CHARS,
        },
    }


def load_viewer_corpus_index(corpus_path: Path) -> dict[str, Any]:
    resolved = corpus_path.resolve()
    sidecar = corpus_index_path(resolved)
    corpus_mtime = file_mtime(resolved)
    index_mtime = file_mtime(sidecar)
    key = (str(resolved), corpus_mtime, index_mtime)
    cached = _CORPUS_INDEX_CACHE.get(key)
    if cached is not None:
        return cached

    if index_mtime >= corpus_mtime and index_mtime > 0:
        try:
            payload = json.loads(sidecar.read_text(encoding="utf-8"))
            if payload.get("index_schema_version") != INDEX_SCHEMA_VERSION:
                payload = corpus_index_from_payload(load_corpus_payload(resolved))
        except (OSError, json.JSONDecodeError):
            payload = corpus_index_from_payload(load_corpus_payload(resolved))
    else:
        payload = corpus_index_from_payload(load_corpus_payload(resolved))
    _CORPUS_INDEX_CACHE.clear()
    _CORPUS_INDEX_CACHE[key] = payload
    return payload


def load_viewer_word_detail(corpus_path: Path, word_text: str) -> dict[str, Any]:
    target = str(word_text or "").strip()
    if not target:
        raise ValueError("Missing word.")
    detail = load_split_word_detail(corpus_path, target)
    if detail:
        return {"word": detail}
    payload = load_corpus_payload(corpus_path)
    for word in payload.get("words") or []:
        if isinstance(word, dict) and word.get("word") == target:
            return {"word": word}
    raise ValueError(f"Word not found: {target}")


def load_viewer_source_details(corpus_path: Path, source_keys: list[str]) -> dict[str, Any]:
    targets = {str(key or "").strip() for key in source_keys if str(key or "").strip()}
    if not targets:
        raise ValueError("Missing source key.")
    sources = []
    missing_targets = set(targets)
    for target in sorted(targets):
        source = load_split_source_detail(corpus_path, target)
        if source:
            source.setdefault("source_key", source_document_key(source))
            sources.append(source)
            missing_targets.discard(target)
    if not missing_targets:
        return {"sources": sources, "missing": []}
    payload = load_corpus_payload(corpus_path)
    fallback_sources = [
        source
        for source in payload.get("sources") or []
        if isinstance(source, dict) and source_document_key(source) in missing_targets
    ]
    for source in fallback_sources:
        source.setdefault("source_key", source_document_key(source))
    sources.extend(fallback_sources)
    found = {source_document_key(source) for source in sources}
    missing = sorted(targets - found)
    return {"sources": sources, "missing": missing}


def load_split_word_detail(corpus_path: Path, word_text: str) -> dict[str, Any] | None:
    return read_json_dict(word_detail_path(corpus_path.resolve(), word_text))


def load_split_source_detail(corpus_path: Path, source_key: str) -> dict[str, Any] | None:
    return read_json_dict(source_detail_path(corpus_path.resolve(), source_key))


def read_json_dict(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def load_corpus_payload(corpus_path: Path) -> dict[str, Any]:
    resolved = corpus_path.resolve()
    mtime = file_mtime(resolved)
    key = (str(resolved), mtime)
    cached = _CORPUS_PAYLOAD_CACHE.get(key)
    if cached is not None:
        return cached
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    _CORPUS_PAYLOAD_CACHE.clear()
    _CORPUS_PAYLOAD_CACHE[key] = payload
    return payload


def file_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except FileNotFoundError:
        return 0.0


def load_annotation_index(corpus_path: Path) -> AnnotationIndex:
    resolved = corpus_path.resolve()
    corpus_mtime = file_mtime(resolved)
    index_mtime = file_mtime(corpus_index_path(resolved))
    key = (str(resolved), corpus_mtime, index_mtime)
    cached = _ANNOTATION_INDEX_CACHE.get(key)
    if cached:
        return cached

    words_by_surface: dict[str, dict[str, Any]] = {}
    payload = load_viewer_corpus_index(resolved)
    word_items = payload.get("words", []) if isinstance(payload, dict) else []
    for word in word_items:
        if not isinstance(word, dict):
            continue
        for surface in corpus_word_surfaces(word):
            existing = words_by_surface.get(surface)
            if not existing or int(word.get("count") or 0) > int(existing.get("count") or 0):
                words_by_surface[surface] = word

    try:
        jlpt_words: JLPTWords | None = load_jlpt_words(DEFAULT_JLPT_WORDS)
    except Exception:
        jlpt_words = None
    try:
        zh_glossary = ChineseGlossary.load(DEFAULT_ZH_DICT)
    except Exception:
        zh_glossary = ChineseGlossary({})

    index = AnnotationIndex(
        words_by_surface=words_by_surface,
        jlpt_words=jlpt_words,
        zh_glossary=zh_glossary,
    )
    _ANNOTATION_INDEX_CACHE.clear()
    _ANNOTATION_INDEX_CACHE[key] = index
    return index


def corpus_word_surfaces(word: dict[str, Any]) -> list[str]:
    surfaces: list[str] = []
    for surface in word.get("annotation_surfaces") or []:
        text = str(surface or "").strip()
        if text:
            surfaces.append(text)
    primary = str(word.get("word") or "").strip()
    if primary:
        surfaces.append(primary)
    notes = word.get("lexical_notes")
    if isinstance(notes, dict):
        for spelling in notes.get("spellings") or []:
            if isinstance(spelling, dict):
                text = str(spelling.get("text") or "").strip()
                if text:
                    surfaces.append(text)
    return list(dict.fromkeys(surfaces))


def annotate_one_text_block(
    text: str,
    *,
    tokenizer: JapaneseTokenizer,
    index: AnnotationIndex,
    study_state: dict[str, Any],
) -> list[dict[str, Any]]:
    ranges: list[dict[str, Any]] = []
    last_end = -1
    tokens = tokenizer.tokenize(text)
    for token_index, token in enumerate(tokens):
        if token.start is None or token.end is None or token.start < last_end:
            continue
        next_token = tokens[token_index + 1] if token_index + 1 < len(tokens) else None
        word = lookup_annotation_word(token, index)
        if not word or not should_annotate_token(token, word, next_token=next_token):
            continue
        ranges.append(
            {
                "start": token.start,
                "end": token.end,
                "surface": text[token.start : token.end],
                "word": word["word"],
                "reading": word.get("reading") or "",
                "level": word.get("level") or "",
                "meaning_zh": word.get("meaning_zh") or "",
                "meaning": word.get("meaning") or "",
                "pos": token.pos or "",
                "status": study_status_for_word(word["word"], study_state),
                "study_count": clamp_study_count(study_state.get("study_counts", {}).get(word["word"], 0)),
            }
        )
        last_end = token.end
    return ranges


def lookup_annotation_word(token: Any, index: AnnotationIndex) -> dict[str, Any] | None:
    for key in dict.fromkeys([token.base, token.surface]):
        if key and key in index.words_by_surface:
            return corpus_annotation_word(index.words_by_surface[key], index.zh_glossary)

    if not index.jlpt_words:
        return None
    jlpt_entry = index.jlpt_words.lookup(token.base, token.surface)
    if not jlpt_entry and is_kana_text(token.surface):
        reading = katakana_to_hiragana(token.reading or token.surface)
        jlpt_entry = index.jlpt_words.lookup_reading(token.surface, reading)
    if not jlpt_entry:
        return None
    return jlpt_annotation_word(jlpt_entry, index.zh_glossary, token.surface, token.base)


def corpus_annotation_word(word: dict[str, Any], zh_glossary: ChineseGlossary) -> dict[str, Any]:
    surface = str(word.get("word") or "").strip()
    level = str(word.get("level") or "").strip()
    if not level and word.get("level_number"):
        level = f"N{word.get('level_number')}"
    meaning_zh = str(word.get("meaning_zh") or "").strip() or (zh_glossary.lookup(surface) or "")
    return {
        "word": surface,
        "reading": str(word.get("reading") or "").strip(),
        "level": level,
        "meaning_zh": meaning_zh,
        "meaning": str(word.get("meaning") or "").strip(),
        "count": int(word.get("count") or 0),
    }


def jlpt_annotation_word(
    entry: WordEntry,
    zh_glossary: ChineseGlossary,
    surface: str | None,
    base: str | None,
) -> dict[str, Any]:
    meaning_zh = zh_glossary.lookup(entry.surface, base, surface) or ""
    return {
        "word": entry.surface,
        "reading": entry.reading or "",
        "level": entry.level_label,
        "meaning_zh": meaning_zh,
        "meaning": entry.meaning or "",
        "count": 0,
    }


def should_annotate_token(token: Any, word: dict[str, Any], *, next_token: Any | None = None) -> bool:
    surface = str(token.surface or "")
    canonical = str(word.get("word") or "")
    if not surface or not JAPANESE_RE.search(surface):
        return False
    if token.pos in ANNOTATION_EXCLUDED_POS:
        return False
    if is_likely_name_before_title(surface, next_token):
        return False
    if len(surface) <= 1 and not KANJI_RE.search(surface + canonical):
        return False
    return True


def is_kana_text(value: str | None) -> bool:
    text = str(value or "")
    return bool(text) and not KANJI_RE.search(text) and bool(re.fullmatch(r"[\u3040-\u30ffー]+", text))


def is_likely_name_before_title(surface: str, next_token: Any | None) -> bool:
    if not next_token or not surface or not KATAKANA_RE.search(surface):
        return False
    title = str(next_token.surface or next_token.base or "")
    return title in NAME_TITLE_SURFACES


def katakana_to_hiragana(value: str | None) -> str:
    text = str(value or "")
    return KATAKANA_RE.sub(lambda match: chr(ord(match.group(0)) - 0x60), text)


def compact_reader_word(word: dict[str, Any]) -> dict[str, Any]:
    return {
        "word": text_limit(word.get("word"), 80),
        "reading": text_limit(word.get("reading"), 120),
        "level": text_limit(word.get("level"), 12),
        "meaning_zh": text_limit(word.get("meaning_zh"), 500),
        "meaning": text_limit(word.get("meaning"), 500),
    }


def compact_reader_example(example: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_type": text_limit(example.get("source_type"), 24),
        "source_title": text_limit(example.get("source_title"), 180),
        "source_artist": text_limit(example.get("source_artist"), 180),
        "source_album": text_limit(example.get("source_album"), 180),
        "subtitle_file": text_limit(example.get("subtitle_file") or example.get("source_file"), 240),
        "episode": example.get("episode") if isinstance(example.get("episode"), int) else None,
        "start_ms": example.get("start_ms") if isinstance(example.get("start_ms"), int) else None,
        "matched_text": text_limit(example.get("matched_text"), 80),
        "sentence": text_limit(example.get("sentence"), 1600),
        "context_before": text_list_limit(example.get("context_before"), item_limit=800, count_limit=4),
        "context_after": text_list_limit(example.get("context_after"), item_limit=800, count_limit=4),
    }


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
        existing_hash = metadata.get("content_sha256") or imported_text_hash(clean_imported_text(path.read_text(encoding="utf-8", errors="replace")))
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


def text_list_limit(value: Any, *, item_limit: int, count_limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text_limit(item, item_limit) for item in value[:count_limit] if str(item or "").strip()]


def normalize_maintenance_spec(raw: dict[str, Any]) -> dict[str, Any]:
    task_type = str(raw.get("type") or "")
    if task_type not in ALLOWED_MAINTENANCE_TASKS:
        raise ValueError(f"Unsupported maintenance task: {task_type}")
    return {
        "type": task_type,
        "limit": optional_clamped_int(raw.get("limit"), minimum=1, maximum=50000),
        "concurrency": clamp_int(raw.get("concurrency"), default=4, minimum=1, maximum=16),
        "overwrite": bool(raw.get("overwrite", False)),
    }


def public_maintenance_spec(spec: dict[str, Any]) -> dict[str, Any]:
    return dict(spec)


def composite_maintenance_steps(spec: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    lyric_spec = {
        "type": "fetch_lyrics",
        "limit": spec["limit"],
        "concurrency": spec["concurrency"],
        "overwrite": spec["overwrite"],
    }
    sync_steps = [
        ("Sync Bangumi anime and subtitles", {"type": "sync_anime"}),
        ("Sync Bangumi music tracks", {"type": "sync_music"}),
        ("Fetch missing LRCLIB lyrics", lyric_spec),
        ("Export refreshed corpus", {"type": "export_corpus"}),
    ]
    if spec["type"] == "sync_media":
        return sync_steps
    if spec["type"] == "refresh_all":
        return [
            ("Update Anime Offline Database", {"type": "fetch_anime_db"}),
            ("Update Japanese-Chinese dictionary", {"type": "fetch_zh_dict"}),
            ("Update JLPT word list", {"type": "fetch_jlpt_words"}),
            ("Update lexical resources", {"type": "fetch_lexical_resources"}),
            *sync_steps,
        ]
    raise ValueError(f"Unsupported composite maintenance task: {spec['type']}")


def clamp_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return min(max(number, minimum), maximum)


def optional_clamped_int(value: Any, *, minimum: int, maximum: int) -> int | None:
    if value in (None, ""):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return min(max(number, minimum), maximum)
