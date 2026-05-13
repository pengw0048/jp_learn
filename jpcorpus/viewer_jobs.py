from __future__ import annotations

import json
import os
import re
import threading
import unicodedata
import uuid
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any

from .llm import (
    DEFAULT_ANTHROPIC_BASE_URL,
    DEFAULT_ANTHROPIC_MODEL,
    AnthropicClient,
    AppleFoundationModelsClient,
    LLMConfig,
    OpenAICompatibleClient,
)
from .paths import DEFAULT_STATE_DB, ensure_parent
from .texts import normalize_display_text


ALLOWED_PROVIDERS = {"openai-compatible", "anthropic", "apple"}
ALLOWED_MAINTENANCE_TASKS = {
    "sync_media",
    "refresh_all",
    "sync_anime",
    "sync_music",
    "fetch_lyrics",
    "export_corpus",
    "fetch_anime_db",
    "fetch_zh_dict",
    "fetch_jlpt_words",
    "fetch_jmdict",
    "fetch_kanjidic2",
    "fetch_lexical_resources",
}
CORPUS_RELOAD_TASKS = {"export_corpus"}
CONFIG_ENV_PATH = Path(".env")
DEFAULT_WEB_TEXT_DIR = Path("texts") / "web"
MAX_IMPORTED_TEXT_CHARS = 1_500_000


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

    def _run_export_corpus_file(self, job: ViewerJob, output: Path) -> dict[str, Any]:
        from . import cli as cli_tasks

        return self._run_callable(
            job,
            "Export corpus",
            cli_tasks.export_corpus_json,
            output=output,
            state_db=self.state_db,
            jlpt_words=cli_tasks.DEFAULT_JLPT_WORDS,
            level=None,
            limit=None,
            examples_per_word=5,
            context_lines=2,
            context_min_chars=40,
            context_max_lines=4,
            zh_dict=cli_tasks.DEFAULT_ZH_DICT,
            jmdict=cli_tasks.DEFAULT_JMDICT,
            kanjidic2=cli_tasks.DEFAULT_KANJIDIC2,
            lexical_notes=True,
            subtitles=None,
            texts=None,
            text_dir=cli_tasks.DEFAULT_TEXTS_DIR,
        )

    def _run_maintenance_task(self, job: ViewerJob, spec: dict[str, Any]) -> dict[str, Any]:
        from . import cli as cli_tasks

        task_type = spec["type"]
        if task_type == "sync_anime":
            return self._run_callable(
                job,
                "Sync Bangumi anime and subtitles",
                cli_tasks.sync,
                state_db=self.state_db,
                anime_db=cli_tasks.DEFAULT_ANIME_DB,
                cache_dir=cli_tasks.DEFAULT_JIMAKU_CACHE,
                max_shows=None,
                max_files_per_show=24,
                download_subtitles=True,
            )
        if task_type == "sync_music":
            return self._run_callable(
                job,
                "Sync Bangumi music tracks",
                cli_tasks.sync_lyrics,
                state_db=self.state_db,
                max_albums=None,
                max_tracks=None,
            )
        if task_type == "fetch_lyrics":
            return self._run_callable(
                job,
                "Fetch missing LRCLIB lyrics",
                cli_tasks.fetch_lyrics,
                state_db=self.state_db,
                cache_dir=cli_tasks.DEFAULT_LYRICS_CACHE,
                limit=spec["limit"],
                overwrite=spec["overwrite"],
                force=False,
                concurrency=spec["concurrency"],
            )
        if task_type == "fetch_anime_db":
            return self._run_callable(
                job,
                "Update Anime Offline Database",
                cli_tasks.fetch_anime_db,
                output=cli_tasks.DEFAULT_ANIME_DB,
            )
        if task_type == "fetch_zh_dict":
            return self._run_callable(
                job,
                "Update Japanese-Chinese dictionary",
                cli_tasks.fetch_zh_dict,
                output=cli_tasks.DEFAULT_ZH_DICT,
                source_url="https://raw.githubusercontent.com/lxl66566/Japanese-Chinese-thesaurus/main/final.json",
            )
        if task_type == "fetch_jlpt_words":
            return self._run_callable(
                job,
                "Update JLPT word list",
                cli_tasks.fetch_jlpt_words,
                output=cli_tasks.DEFAULT_JLPT_WORDS,
                source_url="https://raw.githubusercontent.com/elzup/jlpt-word-list/master/out/all.csv",
            )
        if task_type == "fetch_jmdict":
            return self._run_callable(
                job,
                "Update JMdict",
                cli_tasks.fetch_jmdict,
                output=cli_tasks.DEFAULT_JMDICT,
                source_url="http://ftp.edrdg.org/pub/Nihongo/JMdict_e_examp.gz",
            )
        if task_type == "fetch_kanjidic2":
            return self._run_callable(
                job,
                "Update KANJIDIC2",
                cli_tasks.fetch_kanjidic2,
                output=cli_tasks.DEFAULT_KANJIDIC2,
                source_url="http://ftp.edrdg.org/pub/Nihongo/kanjidic2.xml.gz",
            )
        if task_type == "fetch_lexical_resources":
            return self._run_callable(
                job,
                "Update lexical resources",
                cli_tasks.fetch_lexical_resources,
                jmdict_output=cli_tasks.DEFAULT_JMDICT,
                kanjidic2_output=cli_tasks.DEFAULT_KANJIDIC2,
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
        explanation = client.annotate_example(compact_word, compact_example)
        return {"explanation": explanation}
    finally:
        close_client = getattr(client, "close", None)
        if callable(close_client):
            close_client()


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
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = unique_import_path(directory / f"{timestamp}-{slugify_import_title(title)}.txt")
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    metadata = {
        "source": "web",
        "title": title,
        "url": url,
        "imported_at": _now_iso(),
        "characters": len(text),
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
    }


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


def text_limit(value: Any, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def text_list_limit(value: Any, *, item_limit: int, count_limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text_limit(item, item_limit) for item in value[:count_limit] if str(item or "").strip()]


def viewer_config_status() -> dict[str, Any]:
    bangumi_missing = [
        key
        for key in ("JPCORPUS_BANGUMI_CLIENT_ID", "JPCORPUS_BANGUMI_CLIENT_SECRET")
        if not os.environ.get(key)
    ]
    jimaku_missing = [] if os.environ.get("JIMAKU_API_KEY") else ["JIMAKU_API_KEY"]
    llm = llm_config_status()
    llm_missing = llm_missing_keys(llm["provider"])
    return {
        "env_path": str(CONFIG_ENV_PATH.resolve()),
        "services": [
            {
                "id": "bangumi",
                "label": "Bangumi",
                "configured": not bangumi_missing,
                "missing": bangumi_missing,
            },
            {
                "id": "jimaku",
                "label": "Jimaku subtitles",
                "configured": not jimaku_missing,
                "missing": jimaku_missing,
            },
            {
                "id": "llm",
                "label": "AI explanation",
                "configured": not llm_missing,
                "missing": llm_missing,
            },
        ],
        "llm": llm,
    }


def llm_config_status() -> dict[str, Any]:
    provider = os.environ.get("JPCORPUS_LLM_PROVIDER", "openai-compatible")
    if provider == "anthropic":
        model = os.environ.get("ANTHROPIC_MODEL") or DEFAULT_ANTHROPIC_MODEL
        base_url = (
            os.environ.get("JPCORPUS_ANTHROPIC_BASE_URL")
            or os.environ.get("ANTHROPIC_BASE_URL")
            or DEFAULT_ANTHROPIC_BASE_URL
        )
        api_key_configured = bool(os.environ.get("ANTHROPIC_API_KEY"))
    elif provider == "apple":
        model = "apple"
        base_url = ""
        api_key_configured = True
    else:
        provider = "openai-compatible"
        model = os.environ.get("JPCORPUS_LLM_MODEL") or ""
        base_url = os.environ.get("JPCORPUS_LLM_BASE_URL", "https://api.openai.com/v1")
        api_key_configured = bool(
            os.environ.get("JPCORPUS_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
        )
    return {
        "provider": provider,
        "model": model,
        "base_url": base_url,
        "api_key_configured": api_key_configured,
    }


def llm_missing_keys(provider: str) -> list[str]:
    if provider == "apple":
        return []
    if provider == "anthropic":
        return ["ANTHROPIC_API_KEY"] if not os.environ.get("ANTHROPIC_API_KEY") else []
    missing = []
    if not os.environ.get("JPCORPUS_LLM_MODEL"):
        missing.append("JPCORPUS_LLM_MODEL")
    if not (os.environ.get("JPCORPUS_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")):
        missing.append("JPCORPUS_LLM_API_KEY")
    return missing


def save_viewer_config(raw: dict[str, Any]) -> dict[str, Any]:
    updates: dict[str, str] = {}
    add_optional_update(updates, "JPCORPUS_BANGUMI_CLIENT_ID", raw.get("bangumi_client_id"))
    add_optional_update(updates, "JPCORPUS_BANGUMI_CLIENT_SECRET", raw.get("bangumi_client_secret"))
    add_optional_update(updates, "JIMAKU_API_KEY", raw.get("jimaku_api_key"))
    provider = str(raw.get("llm_provider") or "").strip()
    if provider:
        if provider not in ALLOWED_PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider}")
        updates["JPCORPUS_LLM_PROVIDER"] = provider
    else:
        provider = os.environ.get("JPCORPUS_LLM_PROVIDER", "openai-compatible")
    llm_model = raw.get("llm_model")
    llm_base_url = raw.get("llm_base_url")
    llm_api_key = raw.get("llm_api_key")
    if provider == "anthropic":
        add_optional_update(updates, "ANTHROPIC_MODEL", llm_model)
        add_optional_update(updates, "ANTHROPIC_BASE_URL", llm_base_url)
        add_optional_update(updates, "ANTHROPIC_API_KEY", llm_api_key)
    elif provider == "openai-compatible":
        add_optional_update(updates, "JPCORPUS_LLM_MODEL", llm_model)
        add_optional_update(updates, "JPCORPUS_LLM_BASE_URL", llm_base_url)
        add_optional_update(updates, "JPCORPUS_LLM_API_KEY", llm_api_key)
    if updates:
        write_env_updates(CONFIG_ENV_PATH, updates)
        os.environ.update(updates)
    return viewer_config_status()


def add_optional_update(updates: dict[str, str], key: str, value: Any) -> None:
    if value is None:
        return
    text = str(value).strip()
    if text:
        updates[key] = text


def write_env_updates(path: Path, updates: dict[str, str]) -> None:
    remaining = dict(updates)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    rewritten: list[str] = []
    for line in lines:
        key = env_line_key(line)
        if key and key in remaining:
            rewritten.append(f"{key}={quote_env_value(remaining.pop(key))}")
        else:
            rewritten.append(line)
    if remaining:
        if rewritten and rewritten[-1].strip():
            rewritten.append("")
        rewritten.append("# Added by the local jpcorpus viewer.")
        for key, value in remaining.items():
            rewritten.append(f"{key}={quote_env_value(value)}")
    path.write_text("\n".join(rewritten).rstrip() + "\n", encoding="utf-8")


def env_line_key(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key, _value = stripped.split("=", 1)
    key = key.strip()
    return key or None


def quote_env_value(value: str) -> str:
    if value and all(char.isalnum() or char in "-_./:@+" for char in value):
        return value
    return json.dumps(value, ensure_ascii=False)


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


def resolve_llm_client(*, provider: str, model: Any = None, use_show_context: bool = False) -> Any:
    if provider == "apple":
        return AppleFoundationModelsClient(use_show_context=use_show_context)
    if provider == "anthropic":
        resolved_model = model or os.environ.get("ANTHROPIC_MODEL") or DEFAULT_ANTHROPIC_MODEL
        base_url = (
            os.environ.get("JPCORPUS_ANTHROPIC_BASE_URL")
            or os.environ.get("ANTHROPIC_BASE_URL")
            or DEFAULT_ANTHROPIC_BASE_URL
        )
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("Set ANTHROPIC_API_KEY before using Anthropic AI explanation.")
        return AnthropicClient(
            LLMConfig(
                model=resolved_model,
                base_url=base_url,
                api_key=api_key,
                use_show_context=use_show_context,
            )
        )
    if provider == "openai-compatible":
        resolved_model = model or os.environ.get("JPCORPUS_LLM_MODEL")
        if not resolved_model:
            raise ValueError("Set JPCORPUS_LLM_MODEL before using OpenAI-compatible AI explanation.")
        base_url = os.environ.get("JPCORPUS_LLM_BASE_URL", "https://api.openai.com/v1")
        api_key = os.environ.get("JPCORPUS_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if "api.openai.com" in base_url and not api_key:
            raise ValueError("Set JPCORPUS_LLM_API_KEY or OPENAI_API_KEY before using AI explanation.")
        return OpenAICompatibleClient(
            LLMConfig(
                model=resolved_model,
                base_url=base_url,
                api_key=api_key,
                use_show_context=use_show_context,
            )
        )
    raise ValueError(f"Unsupported provider: {provider}")


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
