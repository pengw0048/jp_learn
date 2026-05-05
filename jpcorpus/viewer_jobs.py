from __future__ import annotations

import json
import os
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
)
from .paths import DEFAULT_STATE_DB, ensure_parent
from .state import State


ALLOWED_ANNOTATION_SCOPES = {"current_word", "filtered_words", "first_unannotated"}
ALLOWED_SOURCES = {"all", "subtitle", "lyrics"}
ALLOWED_LEVELS = {"all", "N5", "N4", "N3", "N2", "N1"}
ALLOWED_PROVIDERS = {"openai-compatible", "anthropic", "apple"}


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
            cache_context, client = resolve_annotation_runtime(spec)
            if spec["cache_only"]:
                payload, annotated = apply_cached_annotations(
                    payload,
                    cache_state=State(self.state_db),
                    cache_context=cache_context,
                    limit=spec["limit"],
                    overwrite=spec["overwrite"],
                    include_example=include_example,
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
                    include_example=include_example,
                    concurrency=spec["concurrency"],
                    request_interval_seconds=(60.0 / spec["rpm"]) if spec.get("rpm") else 0.0,
                    on_error=on_error,
                )
                self._log(job, f"Annotated {annotated} examples with {len(errors)} failures.")
            write_corpus_atomic(self.corpus_path, payload)
            self._finish(job, "succeeded", {"annotated": annotated, "selected": selected_count})
        except Exception as exc:
            self._log(job, f"Job failed: {exc}")
            self._finish(job, "failed", {}, error=str(exc))
        finally:
            close_client = getattr(client, "close", None)
            if callable(close_client):
                close_client()

    def _log(self, job: ViewerJob, message: str) -> None:
        timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        with self._lock:
            job.log.append(f"{timestamp} {message}")

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
    if scope in {"current_word", "filtered_words"} and not words:
        raise ValueError("This annotation scope requires at least one word.")
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
        "source": source,
        "level": level,
        "limit": limit,
        "concurrency": concurrency,
        "rpm": rpm_value,
        "cache_only": bool(raw.get("cache_only", True)),
        "overwrite": bool(raw.get("overwrite", False)),
        "use_show_context": bool(raw.get("use_show_context", False)),
    }


def public_annotation_spec(spec: dict[str, Any]) -> dict[str, Any]:
    public = dict(spec)
    public["word_count"] = len(public.pop("words", []))
    return public


def build_annotation_predicate(spec: dict[str, Any]):
    word_set = set(spec["words"]) if spec["scope"] in {"current_word", "filtered_words"} else None
    source = spec["source"]
    level = spec["level"]

    def include_example(word: dict[str, Any], example: dict[str, Any]) -> bool:
        if word_set is not None and str(word.get("word") or "") not in word_set:
            return False
        if level != "all" and word.get("level") != level:
            return False
        if source != "all" and example.get("source_type") != source:
            return False
        return True

    return include_example


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


def clamp_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return min(max(number, minimum), maximum)
