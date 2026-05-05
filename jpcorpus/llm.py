from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import httpx

from .paths import ensure_parent


ANNOTATION_FIELDS = ("translation_zh", "usage_note_zh", "scene_description")


@dataclass(frozen=True)
class LLMConfig:
    model: str
    base_url: str = "https://api.openai.com/v1"
    api_key: str | None = None
    timeout: float = 60.0

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
                        "You annotate Japanese subtitle examples for Chinese-speaking JLPT learners. "
                        "Return strict JSON only."
                    ),
                },
                {"role": "user", "content": build_annotation_prompt(word, example)},
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


def build_annotation_prompt(word: dict[str, Any], example: dict[str, Any]) -> str:
    context_before = "\n".join(example.get("context_before") or [])
    context_after = "\n".join(example.get("context_after") or [])
    return (
        "Annotate this Japanese subtitle example.\n\n"
        f"Word: {word.get('word')}\n"
        f"Reading: {word.get('reading')}\n"
        f"JLPT level: {word.get('level')}\n"
        f"Chinese meaning: {word.get('meaning_zh') or ''}\n"
        f"English meaning: {word.get('meaning') or ''}\n"
        f"Matched text in sentence: {example.get('matched_text') or ''}\n\n"
        f"Previous subtitle lines:\n{context_before or '(none)'}\n\n"
        f"Current line:\n{example.get('sentence') or ''}\n\n"
        f"Next subtitle lines:\n{context_after or '(none)'}\n\n"
        "Return JSON with exactly these string fields:\n"
        "- translation_zh: natural Chinese translation of the current line only.\n"
        "- usage_note_zh: one short Chinese note explaining how the target word is used here.\n"
        "- scene_description: one short Chinese description of the likely scene/context.\n"
        "Keep each field concise. Do not invent episode facts beyond the provided subtitles."
    )


def parse_annotation_response(content: str) -> dict[str, str]:
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    payload = json.loads(content)
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
) -> tuple[dict[str, Any], int]:
    annotated = 0
    for word in payload.get("words", []):
        for example in word.get("examples", []):
            if annotated >= limit:
                break
            if not overwrite and _has_annotations(example):
                continue
            annotations = client.annotate_example(word, example)
            for field, value in annotations.items():
                if overwrite or not example.get(field):
                    example[field] = value
            annotated += 1
        if annotated >= limit:
            break
    payload["schema_version"] = max(int(payload.get("schema_version") or 0), 4)
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
) -> int:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    payload, annotated = annotate_corpus(
        payload,
        client=client,
        limit=limit,
        overwrite=overwrite,
    )
    ensure_parent(output_path)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return annotated


def _has_annotations(example: dict[str, Any]) -> bool:
    return all(example.get(field) for field in ANNOTATION_FIELDS)


def _clean_annotation_value(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()
