from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import httpx

from .paths import ensure_parent


ANNOTATION_FIELDS = ("translation_zh", "usage_note_zh", "scene_description")
ANNOTATION_CACHE_PURPOSE = "llm-annotation"
ANNOTATION_CACHE_VERSION = 1
APPLE_FM_SCRIPT = Path(__file__).with_name("apple_fm_annotate.swift")


@dataclass(frozen=True)
class LLMConfig:
    model: str
    base_url: str = "https://api.openai.com/v1"
    api_key: str | None = None
    timeout: float = 60.0
    use_show_context: bool = False

    @property
    def chat_completions_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/chat/completions"


class AnnotationClient(Protocol):
    def annotate_example(self, word: dict[str, Any], example: dict[str, Any]) -> dict[str, str]:
        ...


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
                        "You annotate Japanese media examples for Chinese-speaking JLPT learners. "
                        "Return strict JSON only."
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
        with httpx.Client(timeout=self.config.timeout, follow_redirects=True) as client:
            response = client.post(self.config.chat_completions_url, headers=headers, json=payload)
            response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return parse_annotation_response(content)


class AppleFoundationModelsClient:
    def __init__(self, *, timeout: float = 120.0, use_show_context: bool = False) -> None:
        self.timeout = timeout
        self.use_show_context = use_show_context

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
        result = subprocess.run(
            ["xcrun", "swift", str(APPLE_FM_SCRIPT)],
            input=json.dumps(payload, ensure_ascii=False),
            text=True,
            capture_output=True,
            timeout=self.timeout,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Apple Foundation Models request failed.")
        return parse_annotation_response(result.stdout)


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
            "Show context for scene only; trust the subtitle text if there is any conflict:\n"
            f"Summary: {show_summary or '(none)'}\n"
            f"Characters: {show_characters or '(none)'}\n\n"
        )
    return (
        "Annotate this Japanese media example.\n\n"
        f"Word: {word.get('word')}\n"
        f"Reading: {word.get('reading')}\n"
        f"JLPT level: {word.get('level')}\n"
        f"Chinese meaning: {word.get('meaning_zh') or ''}\n"
        f"English meaning: {word.get('meaning') or ''}\n"
        f"Matched text in sentence: {example.get('matched_text') or ''}\n\n"
        f"Previous source blocks:\n{context_before or '(none)'}\n\n"
        f"Current source block:\n{example.get('sentence') or ''}\n\n"
        f"Next source blocks:\n{context_after or '(none)'}\n\n"
        f"{show_context_block}"
        "Return JSON with exactly these string fields:\n"
        "- translation_zh: natural Simplified Chinese translation of the full current source block only; preserve names and question tone; do not omit content; do not translate honorifics like さん as 小姐 or 先生 unless gender/title is explicit.\n"
        "- usage_note_zh: one short Chinese note explaining the target word's meaning or grammar in this source block.\n"
        "- scene_description: one short Chinese description based on the full provided subtitle context.\n"
        "Keep each field concise. Do not invent setting, genre, speaker identity, or hidden episode facts. "
        "If the scene is unclear, say that it is unclear."
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
    return {
        field: _clean_annotation_value(payload.get(field))
        for field in ANNOTATION_FIELDS
    }


def annotate_corpus(
    payload: dict[str, Any],
    *,
    client: AnnotationClient,
    limit: int,
    overwrite: bool = False,
    cache_state: Any | None = None,
    cache_context: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], int]:
    annotated = 0
    for word in payload.get("words", []):
        for example in word.get("examples", []):
            if annotated >= limit:
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
                if cached and cached["status"] == "hit":
                    for field, value in cached["value"].items():
                        if field in ANNOTATION_FIELDS and (overwrite or not example.get(field)):
                            example[field] = value
                    annotated += 1
                    continue
            annotations = client.annotate_example(word, example)
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
) -> int:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    payload, annotated = annotate_corpus(
        payload,
        client=client,
        limit=limit,
        overwrite=overwrite,
        cache_state=cache_state,
        cache_context=cache_context,
    )
    ensure_parent(output_path)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return annotated


def _has_annotations(example: dict[str, Any]) -> bool:
    return all(example.get(field) for field in ANNOTATION_FIELDS)


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
