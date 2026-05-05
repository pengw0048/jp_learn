from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .analysis import CorpusAnalysis, WordExample, WordStats
from .paths import ensure_parent
from .zh_dict import ChineseGlossary


SCHEMA_VERSION = 4


def analysis_to_dict(
    analysis: CorpusAnalysis,
    *,
    level: int | None = None,
    limit: int | None = None,
    examples_per_word: int = 3,
    zh_glossary: ChineseGlossary | None = None,
) -> dict[str, Any]:
    words = _export_words(analysis, level=level)
    if limit is not None:
        words = words[:limit]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "watched_show_count": analysis.watched_show_count,
            "subtitle_show_count": analysis.subtitle_show_count,
            "subtitle_file_count": analysis.subtitle_file_count,
            "total_tokens": analysis.total_tokens,
            "unique_token_count": analysis.unique_token_count,
            "jlpt_coverage": {
                f"N{level_number}": analysis.coverage(level_number)
                for level_number in range(5, 0, -1)
            },
        },
        "shows": [
            {
                "title": show.title,
                "subtitle_file_count": show.file_count,
                "total_tokens": show.total_tokens,
                "unique_jlpt_word_count": len(show.unique_words),
                "jlpt_hits": {
                    f"N{level_number}": show.jlpt_counts.get(level_number, 0)
                    for level_number in range(5, 0, -1)
                },
            }
            for show in sorted(analysis.show_stats.values(), key=lambda item: item.title)
        ],
        "words": [
            _word_to_dict(word, examples_per_word=examples_per_word, zh_glossary=zh_glossary)
            for word in words
        ],
    }


def write_corpus_json(
    analysis: CorpusAnalysis,
    output: Path,
    *,
    level: int | None = None,
    limit: int | None = None,
    examples_per_word: int = 3,
    zh_glossary: ChineseGlossary | None = None,
) -> Path:
    ensure_parent(output)
    payload = analysis_to_dict(
        analysis,
        level=level,
        limit=limit,
        examples_per_word=examples_per_word,
        zh_glossary=zh_glossary,
    )
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def _export_words(analysis: CorpusAnalysis, *, level: int | None) -> list[WordStats]:
    words_by_surface = dict(analysis.word_stats)
    for entry in analysis.jlpt_words.by_surface.values():
        if level is not None and entry.level != level:
            continue
        words_by_surface.setdefault(entry.surface, WordStats(entry=entry))
    words = list(words_by_surface.values())
    if level is not None:
        words = [word for word in words if word.entry.level == level]
    words.sort(key=lambda item: (-item.count, item.entry.level, item.entry.surface))
    return words


def _word_to_dict(
    word: WordStats,
    *,
    examples_per_word: int,
    zh_glossary: ChineseGlossary | None,
) -> dict[str, Any]:
    return {
        "word": word.entry.surface,
        "reading": word.display_reading,
        "level": f"N{word.entry.level}",
        "level_number": word.entry.level,
        "meaning": word.entry.meaning,
        "meaning_zh": _meaning_zh(word, zh_glossary),
        "count": word.count,
        "sources": [
            {"title": title, "count": count}
            for title, count in word.sources.most_common()
        ],
        "examples": [
            _example_to_dict(example)
            for example in _select_examples(word.examples, limit=examples_per_word)
        ],
    }


def _select_examples(examples: list[WordExample], *, limit: int) -> list[WordExample]:
    remaining = list(examples)
    selected: list[WordExample] = []
    selected_sources: set[str] = set()
    while remaining and len(selected) < limit:
        diverse_pool = [
            example for example in remaining if example.source_title not in selected_sources
        ]
        pool = diverse_pool or remaining
        best = max(pool, key=_example_quality_score)
        selected.append(best)
        selected_sources.add(best.source_title)
        remaining.remove(best)
    return selected


def _example_quality_score(example: WordExample) -> float:
    sentence = example.sentence.strip()
    length = len(sentence)
    score = 0.0
    if example.matched_text and example.matched_text in sentence:
        score += 4
    if 8 <= length <= 80:
        score += 6
    elif 4 <= length <= 120:
        score += 3
    score -= abs(length - 32) / 24
    score += min(len(example.context_before), 2) * 0.75
    score += min(len(example.context_after), 2) * 0.75
    if example.start_ms is not None:
        score += 0.5
    if sentence.endswith(("。", "！", "？", "!", "?")):
        score += 0.5
    return score


def _meaning_zh(word: WordStats, zh_glossary: ChineseGlossary | None) -> str | None:
    if zh_glossary:
        meaning = zh_glossary.lookup(word.entry.surface, word.display_reading)
        if meaning:
            return meaning
    return word.entry.meaning_zh


def _example_to_dict(example: WordExample) -> dict[str, Any]:
    return {
        "sentence": example.sentence,
        "source_title": example.source_title,
        "subtitle_file": example.subtitle_file,
        "matched_text": example.matched_text,
        "episode": example.episode,
        "start_ms": example.start_ms,
        "end_ms": example.end_ms,
        "context_before": example.context_before,
        "context_after": example.context_after,
        "scene_description": example.scene_description,
        "translation_zh": None,
        "usage_note_zh": None,
        "reference": {
            "source_title": example.source_title,
            "episode": example.episode,
            "start_ms": example.start_ms,
            "end_ms": example.end_ms,
        },
    }
