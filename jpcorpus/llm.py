from __future__ import annotations

import hashlib
import json
import re
import select
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

import httpx

from .paths import APP_DIR, ensure_parent


ANNOTATION_FIELDS = ("translation_zh", "usage_note_zh", "scene_description")
REQUIRED_ANNOTATION_FIELDS = ("translation_zh", "usage_note_zh")
ANNOTATION_CACHE_PURPOSE = "llm-annotation"
ANNOTATION_CACHE_VERSION = 6
APPLE_FM_SCRIPT = Path(__file__).with_name("apple_fm_annotate.swift")
DEFAULT_ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1"
DEFAULT_ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
ANTHROPIC_VERSION = "2023-06-01"
APPLE_FM_BINARY = APP_DIR / "apple_fm_annotate"


@dataclass(frozen=True)
class LLMConfig:
    model: str
    base_url: str = "https://api.openai.com/v1"
    api_key: str | None = None
    timeout: float = 60.0
    use_show_context: bool = False
    transport: httpx.BaseTransport | None = None

    @property
    def chat_completions_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/chat/completions"

    @property
    def anthropic_messages_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/messages"


class AnnotationClient(Protocol):
    def annotate_example(self, word: dict[str, Any], example: dict[str, Any]) -> dict[str, str]:
        ...


class RequestRateLimiter:
    def __init__(self, *, min_interval_seconds: float) -> None:
        self.min_interval_seconds = max(0.0, min_interval_seconds)
        self._lock = threading.Lock()
        self._next_request_at = 0.0

    def wait(self) -> None:
        if self.min_interval_seconds <= 0:
            return
        with self._lock:
            now = time.monotonic()
            if now < self._next_request_at:
                time.sleep(self._next_request_at - now)
                now = time.monotonic()
            self._next_request_at = now + self.min_interval_seconds


class OpenAICompatibleClient:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    def annotate_example(self, word: dict[str, Any], example: dict[str, Any]) -> dict[str, str]:
        payload = {
            "model": self.config.model,
            "temperature": 0.2,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你为中文母语的日语学习者标注日语例句。"
                        "只返回严格 JSON。除原文中复制的日语或英语外，所有字段值都必须使用自然的简体中文，"
                        "不要写英文解释。"
                    ),
                },
                {
                    "role": "user",
                    "content": build_annotation_prompt(
                        word,
                        example,
                        use_show_context=self.config.use_show_context,
                    ),
                },
            ],
        }
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        with httpx.Client(
            timeout=self.config.timeout,
            follow_redirects=True,
            transport=self.config.transport,
        ) as client:
            response = client.post(self.config.chat_completions_url, headers=headers, json=payload)
            response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return parse_annotation_response(content)


class AnthropicClient:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    def annotate_example(self, word: dict[str, Any], example: dict[str, Any]) -> dict[str, str]:
        if not self.config.api_key:
            raise ValueError("Anthropic API key is required.")
        payload = {
            "model": self.config.model,
            "max_tokens": 512,
            "temperature": 0.2,
            "system": (
                "You annotate Japanese media examples for Chinese-speaking JLPT learners. "
                "Return strict JSON only."
            ),
            "messages": [
                {
                    "role": "user",
                    "content": build_annotation_prompt(
                        word,
                        example,
                        use_show_context=self.config.use_show_context,
                    ),
                }
            ],
        }
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.config.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
        }
        with httpx.Client(
            timeout=self.config.timeout,
            follow_redirects=True,
            transport=self.config.transport,
        ) as client:
            response = client.post(self.config.anthropic_messages_url, headers=headers, json=payload)
            if response.is_error:
                detail = _truncate_text(response.text, limit=500)
                raise RuntimeError(
                    f"Anthropic request failed with HTTP {response.status_code}: {detail}"
                )
        content = response.json().get("content") or []
        text_parts = [
            str(item.get("text") or "")
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        ]
        return parse_annotation_response("\n".join(text_parts))


class AppleFoundationModelsClient:
    def __init__(self, *, timeout: float = 120.0, use_show_context: bool = False) -> None:
        self.timeout = timeout
        self.use_show_context = use_show_context
        self._process: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()

    def close(self) -> None:
        process = self._process
        self._process = None
        if process is None:
            return
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)

    def annotate_example(self, word: dict[str, Any], example: dict[str, Any]) -> dict[str, str]:
        payload = {
            "word": word.get("word") or "",
            "reading": word.get("reading") or "",
            "level": word.get("level") or "",
            "meaning_zh": word.get("meaning_zh") or "",
            "meaning": word.get("meaning") or "",
            "matched_text": example.get("matched_text") or "",
            "sentence": example.get("sentence") or "",
            "context_before": example.get("context_before") or [],
            "context_after": example.get("context_after") or [],
            "show_context": example.get("show_context") or {},
            "use_show_context": self.use_show_context,
        }
        with self._lock:
            return self._annotate_with_worker(payload)

    def _annotate_with_worker(self, payload: dict[str, Any]) -> dict[str, str]:
        process = self._worker_process()
        if process.stdin is None or process.stdout is None:
            raise RuntimeError("Apple Foundation Models worker pipes are not available.")
        process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        process.stdin.flush()
        ready, _, _ = select.select([process.stdout], [], [], self.timeout)
        if not ready:
            self.close()
            raise TimeoutError("Apple Foundation Models worker timed out.")
        line = process.stdout.readline()
        if not line:
            self.close()
            raise RuntimeError("Apple Foundation Models worker exited without a response.")
        response = json.loads(line)
        if not response.get("ok"):
            raise RuntimeError(str(response.get("error") or "Apple Foundation Models request failed."))
        return parse_annotation_response(str(response.get("content") or ""))

    def _worker_process(self) -> subprocess.Popen[str]:
        if self._process is not None and self._process.poll() is None:
            return self._process
        binary = ensure_apple_fm_binary()
        self._process = subprocess.Popen(
            [str(binary), "--jsonl-server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        return self._process

    def __del__(self) -> None:
        self.close()


def ensure_apple_fm_binary() -> Path:
    ensure_parent(APPLE_FM_BINARY)
    if (
        APPLE_FM_BINARY.exists()
        and APPLE_FM_BINARY.stat().st_mtime >= APPLE_FM_SCRIPT.stat().st_mtime
    ):
        return APPLE_FM_BINARY
    result = subprocess.run(
        ["xcrun", "swiftc", str(APPLE_FM_SCRIPT), "-o", str(APPLE_FM_BINARY)],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Failed to compile Apple Foundation Models worker.")
    return APPLE_FM_BINARY


def build_annotation_prompt(
    word: dict[str, Any],
    example: dict[str, Any],
    *,
    use_show_context: bool = False,
) -> str:
    context_before = "\n".join(example.get("context_before") or [])
    context_after = "\n".join(example.get("context_after") or [])
    show_context = example.get("show_context") or {}
    show_summary = _truncate_text(show_context.get("summary"), limit=280)
    show_characters = ", ".join(str(item) for item in (show_context.get("characters") or [])[:12])
    show_context_block = ""
    if use_show_context and (show_summary or show_characters):
        show_context_block = (
            "Optional show context for understanding names or references only; trust the source text if there is any conflict:\n"
            f"Summary: {show_summary or '(none)'}\n"
            f"Characters: {show_characters or '(none)'}\n\n"
        )
    return (
        "请标注下面这个日语媒体例句，面向中文母语的日语学习者。\n\n"
        f"目标词: {word.get('word')}\n"
        f"读音: {word.get('reading')}\n"
        f"JLPT 等级: {word.get('level')}\n"
        f"中文释义: {word.get('meaning_zh') or ''}\n"
        f"英文释义，仅用于消歧，禁止照抄到输出中: {word.get('meaning') or ''}\n"
        f"当前句中匹配到的词形: {example.get('matched_text') or ''}\n\n"
        f"前文 source blocks，只能辅助理解，禁止翻译到 translation_zh 中:\n{context_before or '(none)'}\n\n"
        f"当前 source block，只翻译这一段:\n{example.get('sentence') or ''}\n\n"
        f"后文 source blocks，只能辅助理解，禁止翻译到 translation_zh 中:\n{context_after or '(none)'}\n\n"
        f"{show_context_block}"
        "只返回一个 JSON object，必须且只能包含下面三个字符串字段:\n"
        "- translation_zh: 用自然简体中文翻译完整的当前 source block。不要翻译前文或后文。保留人名和疑问语气，不要漏译。除非原文明确性别或身份，不要把 さん 翻成 小姐 或 先生。\n"
        "- usage_note_zh: 用一句简短自然的简体中文说明目标词在当前 source block 里的词义或语法。引用日语表达时，必须原样复制日语，不要把日语汉字改写成中文。\n"
        "- scene_description: 空字符串。\n"
        "要求: 字段内容要简洁；不要编造场景、作品类型、说话人身份或隐藏剧情；"
        "translation_zh 和 usage_note_zh 不要出现英文单词或英文语法，除非原文里本来就有英语。"
    )


def parse_annotation_response(content: str) -> dict[str, str]:
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        payload = parse_loose_annotation_response(content)
    if not isinstance(payload, dict):
        raise ValueError("LLM annotation response must be a JSON object.")
    annotations = {
        field: _clean_annotation_value(payload.get(field))
        for field in ANNOTATION_FIELDS
    }
    missing = [field for field in REQUIRED_ANNOTATION_FIELDS if not annotations[field]]
    if missing:
        raise ValueError(f"LLM annotation response is missing required fields: {', '.join(missing)}")
    return annotations


def annotate_corpus(
    payload: dict[str, Any],
    *,
    client: AnnotationClient,
    limit: int,
    overwrite: bool = False,
    cache_state: Any | None = None,
    cache_context: dict[str, Any] | None = None,
    concurrency: int = 1,
    request_interval_seconds: float = 0.0,
    on_error: Callable[[dict[str, Any], dict[str, Any], Exception], None] | None = None,
) -> tuple[dict[str, Any], int]:
    annotated = 0
    targets: list[tuple[dict[str, Any], dict[str, Any], str | None]] = []
    for word in payload.get("words", []):
        for example in word.get("examples", []):
            if annotated + len(targets) >= limit:
                break
            if not overwrite and _has_annotations(example):
                continue
            cache_key = None
            if cache_state is not None:
                cache_key = annotation_cache_key(word, example, cache_context or {})
                cached = cache_state.get_cache_entry(
                    purpose=ANNOTATION_CACHE_PURPOSE,
                    cache_key=cache_key,
                    version=ANNOTATION_CACHE_VERSION,
                )
                if cached and cached["status"] == "hit" and _has_required_annotations(cached.get("value")):
                    for field, value in cached["value"].items():
                        if field in ANNOTATION_FIELDS and (overwrite or not example.get(field)):
                            example[field] = value
                    annotated += 1
                    continue
            targets.append((word, example, cache_key))
        if annotated + len(targets) >= limit:
            break

    if targets:
        max_workers = max(1, concurrency)
        rate_limiter = RequestRateLimiter(min_interval_seconds=request_interval_seconds)

        def annotate_target(word: dict[str, Any], example: dict[str, Any]) -> dict[str, str]:
            rate_limiter.wait()
            return client.annotate_example(word, example)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(annotate_target, word, example): (word, example, cache_key)
                for word, example, cache_key in targets
            }
            for future in as_completed(futures):
                word, example, cache_key = futures[future]
                try:
                    annotations = future.result()
                except Exception as exc:
                    if on_error is None:
                        raise
                    on_error(word, example, exc)
                    continue
                if cache_state is not None and cache_key is not None:
                    cache_state.save_cache_entry(
                        purpose=ANNOTATION_CACHE_PURPOSE,
                        cache_key=cache_key,
                        version=ANNOTATION_CACHE_VERSION,
                        status="hit",
                        value=annotations,
                    )
                for field, value in annotations.items():
                    if overwrite or not example.get(field):
                        example[field] = value
                annotated += 1

    payload["schema_version"] = max(int(payload.get("schema_version") or 0), 6)
    metadata = payload.setdefault("annotation", {})
    if isinstance(metadata, dict):
        metadata["fields"] = list(ANNOTATION_FIELDS)
    return payload, annotated


def apply_cached_annotations(
    payload: dict[str, Any],
    *,
    cache_state: Any,
    cache_context: dict[str, Any] | None = None,
    limit: int,
    overwrite: bool = False,
) -> tuple[dict[str, Any], int]:
    annotated = 0
    for word in payload.get("words", []):
        for example in word.get("examples", []):
            if annotated >= limit:
                break
            if not overwrite and _has_annotations(example):
                continue
            cache_key = annotation_cache_key(word, example, cache_context or {})
            cached = cache_state.get_cache_entry(
                purpose=ANNOTATION_CACHE_PURPOSE,
                cache_key=cache_key,
                version=ANNOTATION_CACHE_VERSION,
            )
            if not (cached and cached["status"] == "hit" and _has_required_annotations(cached.get("value"))):
                continue
            for field, value in cached["value"].items():
                if field in ANNOTATION_FIELDS and (overwrite or not example.get(field)):
                    example[field] = value
            annotated += 1
        if annotated >= limit:
            break

    payload["schema_version"] = max(int(payload.get("schema_version") or 0), 6)
    metadata = payload.setdefault("annotation", {})
    if isinstance(metadata, dict):
        metadata["fields"] = list(ANNOTATION_FIELDS)
    return payload, annotated


def annotate_corpus_file(
    input_path: Path,
    output_path: Path,
    *,
    client: AnnotationClient,
    limit: int,
    overwrite: bool = False,
    cache_state: Any | None = None,
    cache_context: dict[str, Any] | None = None,
    concurrency: int = 1,
    request_interval_seconds: float = 0.0,
    on_error: Callable[[dict[str, Any], dict[str, Any], Exception], None] | None = None,
) -> int:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    payload, annotated = annotate_corpus(
        payload,
        client=client,
        limit=limit,
        overwrite=overwrite,
        cache_state=cache_state,
        cache_context=cache_context,
        concurrency=concurrency,
        request_interval_seconds=request_interval_seconds,
        on_error=on_error,
    )
    ensure_parent(output_path)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return annotated


def apply_cached_annotations_file(
    input_path: Path,
    output_path: Path,
    *,
    cache_state: Any,
    cache_context: dict[str, Any] | None = None,
    limit: int,
    overwrite: bool = False,
) -> int:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    payload, annotated = apply_cached_annotations(
        payload,
        cache_state=cache_state,
        cache_context=cache_context,
        limit=limit,
        overwrite=overwrite,
    )
    ensure_parent(output_path)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return annotated


def _has_annotations(example: dict[str, Any]) -> bool:
    return all(example.get(field) for field in REQUIRED_ANNOTATION_FIELDS)


def _has_required_annotations(value: Any) -> bool:
    return isinstance(value, dict) and all(
        bool(_clean_annotation_value(value.get(field)))
        for field in REQUIRED_ANNOTATION_FIELDS
    )


def annotation_cache_key(
    word: dict[str, Any],
    example: dict[str, Any],
    context: dict[str, Any],
) -> str:
    payload = {
        "context": context,
        "word": {
            "word": word.get("word") or "",
            "reading": word.get("reading") or "",
            "level": word.get("level") or "",
            "meaning_zh": word.get("meaning_zh") or "",
            "meaning": word.get("meaning") or "",
        },
        "example": {
            "source_type": example.get("source_type") or "",
            "matched_text": example.get("matched_text") or "",
            "sentence": example.get("sentence") or "",
            "context_before": example.get("context_before") or [],
            "context_after": example.get("context_after") or [],
            "show_context": example.get("show_context") or {},
        },
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def parse_loose_annotation_response(content: str) -> dict[str, str]:
    payload = {}
    for line in content.splitlines():
        line = line.strip()
        for field in ANNOTATION_FIELDS:
            prefix = f'"{field}"'
            if not line.startswith(prefix):
                continue
            _, value = line.split(":", 1)
            value = value.strip().rstrip(",").strip()
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            payload[field] = value.replace('\\"', '"').replace("\\n", " ")
    if not payload:
        raise ValueError("LLM annotation response must be JSON or JSON-like key/value lines.")
    return payload


def _clean_annotation_value(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _truncate_text(value: Any, *, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."
