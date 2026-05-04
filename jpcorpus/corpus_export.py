from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .analysis import CorpusAnalysis, WordExample, WordStats
from .paths import ensure_parent


SCHEMA_VERSION = 1


def analysis_to_dict(
    analysis: CorpusAnalysis,
    *,
    level: int | None = None,
    limit: int | None = None,
    examples_per_word: int = 3,
) -> dict[str, Any]:
    words = analysis.top_words(level=level, limit=len(analysis.word_stats))
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
            _word_to_dict(word, examples_per_word=examples_per_word)
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
) -> Path:
    ensure_parent(output)
    payload = analysis_to_dict(
        analysis,
        level=level,
        limit=limit,
        examples_per_word=examples_per_word,
    )
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def _word_to_dict(word: WordStats, *, examples_per_word: int) -> dict[str, Any]:
    return {
        "word": word.entry.surface,
        "reading": word.display_reading,
        "level": f"N{word.entry.level}",
        "level_number": word.entry.level,
        "meaning": word.entry.meaning,
        "count": word.count,
        "sources": [
            {"title": title, "count": count}
            for title, count in word.sources.most_common()
        ],
        "examples": [
            _example_to_dict(example)
            for example in word.examples[:examples_per_word]
        ],
    }


def _example_to_dict(example: WordExample) -> dict[str, Any]:
    return {
        "sentence": example.sentence,
        "source_title": example.source_title,
        "subtitle_file": example.subtitle_file,
        "episode": example.episode,
        "start_ms": example.start_ms,
        "end_ms": example.end_ms,
    }
