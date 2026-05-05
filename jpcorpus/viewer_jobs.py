from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .llm import (
    DEFAULT_ANTHROPIC_BASE_URL,
    DEFAULT_ANTHROPIC_MODEL,
    AnthropicClient,
    AppleFoundationModelsClient,
    LLMConfig,
    OpenAICompatibleClient,
    annotate_corpus,
    apply_cached_annotations,
    apply_cached_annotations_file,
)
from .paths import DEFAULT_STATE_DB, ensure_parent
from .state import State


ALLOWED_ANNOTATION_SCOPES = {
    "current_word",
    "filtered_words",
    "first_unannotated",
    "selected_examples",
}
ALLOWED_SOURCES = {"all", "subtitle", "lyrics"}
ALLOWED_LEVELS = {"all", "N5", "N4", "N3", "N2", "N1"}
ALLOWED_PROVIDERS = {"openai-compatible", "anthropic", "apple"}
EXAMPLE_SELECTION_FIELDS = (
    "source_type",
    "source_title",
    "source_artist",
    "source_album",
    "subtitle_file",
    "episode",
    "start_ms",
    "end_ms",
    "matched_text",
    "sentence",
)
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
}
CORPUS_RELOAD_TASKS = {"annotate", "export_corpus"}


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

    def start_annotation(self, raw_spec: dict[str, Any]) -> dict[str, Any]:
        spec = normalize_annotation_spec(raw_spec)
        with self._lock:
            if self._job and self._job.status == "running":
                raise RuntimeError("Another maintenance job is already running.")
            job = ViewerJob(id=str(uuid.uuid4()), kind="annotate", spec=public_annotation_spec(spec))
            self._job = job
        thread = threading.Thread(target=self._run_annotation_job, args=(job, spec), daemon=True)
        thread.start()
        return job.to_dict()

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

    def _run_annotation_job(self, job: ViewerJob, spec: dict[str, Any]) -> None:
        client: Any | None = None
        try:
            self._log(job, f"Reading corpus: {self.corpus_path}")
            payload = json.loads(self.corpus_path.read_text(encoding="utf-8"))
            include_example = build_annotation_predicate(spec)
            selected_count = count_annotation_targets(
                payload,
                include_example=include_example,
                overwrite=spec["overwrite"],
            )
            self._log(job, f"Selected {selected_count} candidate examples.")
            progress = {
                "phase": "cache" if spec["cache_only"] else "annotate",
                "selected": selected_count,
                "total": min(selected_count, spec["limit"]),
                "completed": 0,
                "cached": 0,
                "annotated": 0,
                "failed": 0,
                "api_targets": None,
                "remaining": min(selected_count, spec["limit"]),
                "percent": 0.0,
            }

            def publish_progress() -> None:
                total = int(progress["total"] or 0)
                completed = int(progress["completed"] or 0)
                progress["remaining"] = max(total - completed, 0)
                progress["percent"] = round((completed / total) * 100, 1) if total else 100.0
                self._set_progress(job, progress)

            def on_annotation_progress(event: str, _details: dict[str, Any]) -> None:
                if event == "targets_ready":
                    progress["api_targets"] = _details.get("api_targets")
                    progress["cached"] = int(_details.get("cached") or progress["cached"])
                    progress["completed"] = int(progress["cached"]) + int(progress["failed"])
                elif event == "cache_hit":
                    progress["cached"] = int(progress["cached"]) + 1
                    progress["completed"] = int(progress["completed"]) + 1
                elif event == "api_hit":
                    progress["annotated"] = int(progress["annotated"]) + 1
                    progress["completed"] = int(progress["completed"]) + 1
                elif event == "failed":
                    progress["failed"] = int(progress["failed"]) + 1
                    progress["completed"] = int(progress["completed"]) + 1
                publish_progress()

            publish_progress()
            cache_context, client = resolve_annotation_runtime(spec)
            if spec["cache_only"]:
                payload, annotated = apply_cached_annotations(
                    payload,
                    cache_state=State(self.state_db),
                    cache_context=cache_context,
                    limit=spec["limit"],
                    overwrite=spec["overwrite"],
                    include_example=include_example,
                    on_progress=on_annotation_progress,
                )
                self._log(job, f"Applied {annotated} cached annotations.")
            else:
                errors = []

                def on_error(word: dict[str, Any], example: dict[str, Any], exc: Exception) -> None:
                    label = word.get("word") or example.get("matched_text") or "example"
                    message = f"Annotation failed for {label}: {exc}"
                    errors.append(message)
                    self._log(job, message)

                payload, annotated = annotate_corpus(
                    payload,
                    client=client,
                    limit=spec["limit"],
                    overwrite=spec["overwrite"],
                    cache_state=State(self.state_db),
                    cache_context=cache_context,
                    bypass_cache=spec["bypass_cache"],
                    include_example=include_example,
                    concurrency=spec["concurrency"],
                    request_interval_seconds=(60.0 / spec["rpm"]) if spec.get("rpm") else 0.0,
                    on_error=on_error,
                    on_progress=on_annotation_progress,
                )
                self._log(job, f"Annotated {annotated} examples with {len(errors)} failures.")
            write_corpus_atomic(self.corpus_path, payload)
            self._finish(
                job,
                "succeeded",
                {"annotated": annotated, "selected": selected_count, "reload_corpus": True},
            )
        except Exception as exc:
            self._log(job, f"Job failed: {exc}")
            self._finish(job, "failed", {}, error=str(exc))
        finally:
            close_client = getattr(client, "close", None)
            if callable(close_client):
                close_client()

    def _run_maintenance_job(self, job: ViewerJob, spec: dict[str, Any]) -> None:
        try:
            if spec["type"] in {"sync_media", "refresh_all"}:
                result = self._run_composite_job(job, spec)
            elif spec["type"] == "export_corpus":
                result = self._run_export_corpus(job)
            else:
                command = maintenance_command(spec)
                result = self._run_command(job, command)
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
                step_result = self._run_command(job, maintenance_command(step_spec))
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
        command = jpcorpus_command() + ["export", "corpus-json", "--output", str(raw_path)]
        self._run_command(job, command)
        served_path = self.corpus_path.resolve()
        if served_path == raw_path.resolve():
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
            return {"output": str(raw_path), "reload_corpus": True}

        self._log(job, f"Applying cached annotations to served corpus: {served_path}")
        cache_context, _client = resolve_annotation_runtime(
            {
                "provider": os.environ.get("JPCORPUS_LLM_PROVIDER") or "openai-compatible",
                "model": os.environ.get("JPCORPUS_LLM_MODEL") or os.environ.get("ANTHROPIC_MODEL"),
                "cache_only": True,
                "use_show_context": False,
            }
        )
        annotated = apply_cached_annotations_file(
            raw_path,
            served_path,
            cache_state=State(self.state_db),
            cache_context=cache_context,
            limit=500000,
            overwrite=False,
        )
        self._log(job, f"Applied {annotated} cached annotations.")
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
        return {
            "output": str(served_path),
            "raw_output": str(raw_path),
            "cached_annotations": annotated,
            "reload_corpus": True,
        }

    def _run_command(self, job: ViewerJob, command: list[str]) -> dict[str, Any]:
        self._log(job, f"Running: {' '.join(command)}")
        process = subprocess.Popen(
            command,
            cwd=Path.cwd(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
        )
        assert process.stdout is not None
        for line in process.stdout:
            line = line.rstrip()
            if line:
                self._log(job, line)
        return_code = process.wait()
        if return_code != 0:
            raise RuntimeError(f"Command exited with status {return_code}.")
        return {"return_code": return_code}

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
        "tasks": sorted(ALLOWED_MAINTENANCE_TASKS | {"annotate"}),
        "llm": {
            "provider": os.environ.get("JPCORPUS_LLM_PROVIDER", "openai-compatible"),
            "model": (
                os.environ.get("JPCORPUS_LLM_MODEL")
                or os.environ.get("ANTHROPIC_MODEL")
                or DEFAULT_ANTHROPIC_MODEL
            ),
            "base_url": os.environ.get("JPCORPUS_LLM_BASE_URL", "https://api.openai.com/v1"),
        },
        "job": runner.current_job() if runner else None,
    }


def normalize_annotation_spec(raw: dict[str, Any]) -> dict[str, Any]:
    scope = str(raw.get("scope") or "current_word")
    if scope not in ALLOWED_ANNOTATION_SCOPES:
        raise ValueError(f"Unsupported annotation scope: {scope}")
    provider = str(raw.get("provider") or os.environ.get("JPCORPUS_LLM_PROVIDER") or "openai-compatible")
    if provider not in ALLOWED_PROVIDERS:
        raise ValueError(f"Unsupported provider: {provider}")
    source = str(raw.get("source") or "all")
    if source not in ALLOWED_SOURCES:
        raise ValueError(f"Unsupported source filter: {source}")
    level = str(raw.get("level") or "all")
    if level not in ALLOWED_LEVELS:
        raise ValueError(f"Unsupported level filter: {level}")
    words = raw.get("words") or []
    if not isinstance(words, list):
        raise ValueError("words must be a list.")
    words = [str(word) for word in words if str(word)]
    if scope in {"current_word", "filtered_words", "selected_examples"} and not words:
        raise ValueError("This annotation scope requires at least one word.")
    examples = raw.get("examples") or []
    if not isinstance(examples, list):
        raise ValueError("examples must be a list.")
    examples = [normalize_example_selector(example) for example in examples]
    if scope == "selected_examples" and not examples:
        raise ValueError("This annotation scope requires at least one example.")
    limit = clamp_int(raw.get("limit"), default=20, minimum=1, maximum=5000)
    concurrency = clamp_int(raw.get("concurrency"), default=1, minimum=1, maximum=16)
    rpm = raw.get("rpm")
    rpm_value = float(rpm) if rpm not in (None, "", 0) else None
    if rpm_value is not None and rpm_value <= 0:
        raise ValueError("rpm must be greater than zero.")
    return {
        "scope": scope,
        "provider": provider,
        "model": str(raw.get("model") or "") or None,
        "words": words[:10000],
        "examples": examples[:1000],
        "source": source,
        "level": level,
        "limit": limit,
        "concurrency": concurrency,
        "rpm": rpm_value,
        "cache_only": bool(raw.get("cache_only", True)),
        "bypass_cache": bool(raw.get("bypass_cache", False)),
        "overwrite": bool(raw.get("overwrite", False)),
        "use_show_context": bool(raw.get("use_show_context", False)),
    }


def public_annotation_spec(spec: dict[str, Any]) -> dict[str, Any]:
    public = dict(spec)
    public["word_count"] = len(public.pop("words", []))
    public["example_count"] = len(public.pop("examples", []))
    return public


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


def build_annotation_predicate(spec: dict[str, Any]):
    word_set = (
        set(spec["words"])
        if spec["scope"] in {"current_word", "filtered_words", "selected_examples"}
        else None
    )
    example_set = (
        {example_selection_key(example) for example in spec.get("examples", [])}
        if spec["scope"] == "selected_examples"
        else None
    )
    source = spec["source"]
    level = spec["level"]

    def include_example(word: dict[str, Any], example: dict[str, Any]) -> bool:
        if word_set is not None and str(word.get("word") or "") not in word_set:
            return False
        if example_set is not None and example_selection_key(example) not in example_set:
            return False
        if level != "all" and word.get("level") != level:
            return False
        if source != "all" and example.get("source_type") != source:
            return False
        return True

    return include_example


def normalize_example_selector(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("examples must contain objects.")
    return {field: normalize_example_selection_value(raw.get(field)) for field in EXAMPLE_SELECTION_FIELDS}


def normalize_example_selection_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def example_selection_key(example: dict[str, Any]) -> str:
    payload = normalize_example_selector(example)
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def count_annotation_targets(
    payload: dict[str, Any],
    *,
    include_example,
    overwrite: bool,
) -> int:
    count = 0
    for word in payload.get("words", []):
        for example in word.get("examples", []):
            if not include_example(word, example):
                continue
            if not overwrite and example.get("translation_zh") and example.get("usage_note_zh"):
                continue
            count += 1
    return count


def resolve_annotation_runtime(spec: dict[str, Any]) -> tuple[dict[str, Any], Any | None]:
    provider = spec["provider"]
    if provider == "apple":
        model = "apple"
        base_url = ""
        client = None if spec["cache_only"] else AppleFoundationModelsClient(
            use_show_context=spec["use_show_context"]
        )
    elif provider == "anthropic":
        model = spec["model"] or os.environ.get("ANTHROPIC_MODEL") or DEFAULT_ANTHROPIC_MODEL
        base_url = os.environ.get("JPCORPUS_ANTHROPIC_BASE_URL") or DEFAULT_ANTHROPIC_BASE_URL
        client = None
        if not spec["cache_only"]:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("Set ANTHROPIC_API_KEY before running Anthropic annotations.")
            client = AnthropicClient(
                LLMConfig(
                    model=model,
                    base_url=base_url,
                    api_key=api_key,
                    use_show_context=spec["use_show_context"],
                )
            )
    elif provider == "openai-compatible":
        model = spec["model"] or os.environ.get("JPCORPUS_LLM_MODEL")
        if not model:
            raise ValueError("Set JPCORPUS_LLM_MODEL before running OpenAI-compatible annotations.")
        base_url = os.environ.get("JPCORPUS_LLM_BASE_URL", "https://api.openai.com/v1")
        client = None
        if not spec["cache_only"]:
            api_key = os.environ.get("JPCORPUS_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
            if "api.openai.com" in base_url and not api_key:
                raise ValueError("Set JPCORPUS_LLM_API_KEY or OPENAI_API_KEY before running annotations.")
            client = OpenAICompatibleClient(
                LLMConfig(
                    model=model,
                    base_url=base_url,
                    api_key=api_key,
                    use_show_context=spec["use_show_context"],
                )
            )
    else:
        raise ValueError(f"Unsupported provider: {provider}")
    return {
        "provider": provider,
        "model": model,
        "base_url": base_url,
        "use_show_context": spec["use_show_context"],
    }, client


def write_corpus_atomic(path: Path, payload: dict[str, Any]) -> None:
    ensure_parent(path)
    temp_path = path.with_name(f".{path.name}.{int(time.time() * 1000)}.tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp_path.replace(path)


def maintenance_command(spec: dict[str, Any]) -> list[str]:
    command = jpcorpus_command()
    task_type = spec["type"]
    if task_type == "sync_anime":
        return command + ["sync"]
    if task_type == "sync_music":
        return command + ["lyrics", "sync"]
    if task_type == "fetch_lyrics":
        args = command + ["lyrics", "fetch", "--concurrency", str(spec["concurrency"])]
        if spec["limit"] is not None:
            args.extend(["--limit", str(spec["limit"])])
        if spec["overwrite"]:
            args.append("--overwrite")
        return args
    if task_type == "fetch_anime_db":
        return command + ["data", "fetch-anime-db"]
    if task_type == "fetch_zh_dict":
        return command + ["data", "fetch-zh-dict"]
    if task_type == "fetch_jlpt_words":
        return command + ["data", "fetch-jlpt-words"]
    raise ValueError(f"Unsupported maintenance task: {task_type}")


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
            *sync_steps,
        ]
    raise ValueError(f"Unsupported composite maintenance task: {spec['type']}")


def jpcorpus_command() -> list[str]:
    script_path = Path(sys.executable).with_name("jpcorpus")
    if script_path.exists():
        return [str(script_path)]
    return ["jpcorpus"]


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
