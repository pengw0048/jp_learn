from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .analysis import CorpusAnalysis, SourceDocument, SourceLine, SourceLineMatch, WordExample, WordStats
from .lexical_notes import (
    LexicalResourceIndex,
    target_kanji_for_words,
    target_keys_for_words,
)
from .models import WordEntry
from .paths import ensure_parent
from .zh_dict import ChineseGlossary


SCHEMA_VERSION = 13
INDEX_SCHEMA_VERSION = 2
DETAIL_WORD_KEYS = {"examples", "lexical_notes", "sources"}
INDEX_WORD_KEYS = {
    "word",
    "reading",
    "level",
    "level_number",
    "meaning",
    "meaning_zh",
    "count",
    "subtitle_count",
    "lyrics_count",
    "text_count",
    "source_count",
    "source_type_counts",
    "status",
    "study_count",
}


def analysis_to_dict(
    analysis: CorpusAnalysis,
    *,
    level: int | None = None,
    limit: int | None = None,
    examples_per_word: int = 5,
    zh_glossary: ChineseGlossary | None = None,
    jmdict_path: Path | None = None,
    kanjidic2_path: Path | None = None,
    include_zero_count_words: bool = True,
) -> dict[str, Any]:
    lexical_index = None
    if jmdict_path or kanjidic2_path:
        lexical_targets = _lexical_target_words(
            analysis,
            level=level,
            include_zero_count_words=include_zero_count_words,
        )
        lexical_index = LexicalResourceIndex.load_optional(
            jmdict_path=jmdict_path,
            kanjidic2_path=kanjidic2_path,
            target_keys=target_keys_for_words(lexical_targets),
            target_kanji=target_kanji_for_words(lexical_targets),
        )
    words = _export_words(
        analysis,
        level=level,
        lexical_index=lexical_index,
        include_zero_count_words=include_zero_count_words,
    )
    if limit is not None:
        words = words[:limit]
    word_payloads = [
        _word_to_dict(
            word,
            examples_per_word=examples_per_word,
            zh_glossary=zh_glossary,
            lexical_index=lexical_index,
        )
        for word in words
    ]
    exported_words = {word["word"] for word in word_payloads if word.get("word")}
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "watched_show_count": analysis.watched_show_count,
            "subtitle_show_count": analysis.subtitle_show_count,
            "subtitle_file_count": analysis.subtitle_file_count,
            "text_file_count": analysis.text_file_count,
            "music_track_count": analysis.music_track_count,
            "lyric_file_count": analysis.lyric_file_count,
            "source_type_counts": dict(analysis.source_type_counts),
            "total_tokens": analysis.total_tokens,
            "unique_token_count": analysis.unique_token_count,
            "jlpt_coverage": {
                f"N{level_number}": analysis.coverage(level_number)
                for level_number in range(5, 0, -1)
            },
            "word_source_coverage": _word_source_coverage(
                analysis,
                word_payloads=word_payloads,
                lexical_index=lexical_index,
            ),
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
        "sources": [
            _source_document_to_dict(document, exported_words=exported_words)
            for document in analysis.source_documents
        ],
        "words": word_payloads,
    }


def write_corpus_json(
    analysis: CorpusAnalysis,
    output: Path,
    *,
    level: int | None = None,
    limit: int | None = None,
    examples_per_word: int = 5,
    zh_glossary: ChineseGlossary | None = None,
    jmdict_path: Path | None = None,
    kanjidic2_path: Path | None = None,
) -> Path:
    ensure_parent(output)
    payload = analysis_to_dict(
        analysis,
        level=level,
        limit=limit,
        examples_per_word=examples_per_word,
        zh_glossary=zh_glossary,
        jmdict_path=jmdict_path,
        kanjidic2_path=kanjidic2_path,
    )
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_corpus_index_json(payload, corpus_index_path(output))
    return output


def corpus_index_path(output: Path) -> Path:
    return output.with_name(f"{output.stem}.index.json")


def write_corpus_index_json(payload: dict[str, Any], output: Path) -> Path:
    ensure_parent(output)
    output.write_text(json.dumps(corpus_index_from_payload(payload), ensure_ascii=False) + "\n", encoding="utf-8")
    return output


def corpus_index_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "index_schema_version": INDEX_SCHEMA_VERSION,
        "schema_version": payload.get("schema_version"),
        "generated_at": payload.get("generated_at"),
        "summary": payload.get("summary") or {},
        "shows": payload.get("shows") or [],
        "sources": [
            _source_index_entry(source)
            for source in payload.get("sources") or []
            if isinstance(source, dict)
        ],
        "words": [
            _word_index_entry(word)
            for word in payload.get("words") or []
            if isinstance(word, dict)
        ],
    }


def _word_index_entry(word: dict[str, Any]) -> dict[str, Any]:
    entry = {
        key: word[key]
        for key in INDEX_WORD_KEYS
        if key in word
    }
    entry["example_count"] = len(word.get("examples") or [])
    entry["has_detail"] = any(key in word for key in DETAIL_WORD_KEYS)
    entry["search_terms"] = _word_search_terms(word)
    return entry


def _word_search_terms(word: dict[str, Any]) -> list[str]:
    terms: list[str] = []

    def add(value: Any) -> None:
        text = str(value or "").strip()
        if text and len(text) <= 300:
            terms.append(text)

    add(word.get("word"))
    add(word.get("reading"))
    add(word.get("meaning_zh"))
    add(word.get("meaning"))
    add(word.get("level"))

    notes = word.get("lexical_notes")
    if isinstance(notes, dict):
        for value in notes.get("parts_of_speech") or []:
            add(value)
        for form in notes.get("spellings") or []:
            if isinstance(form, dict):
                add(form.get("text"))
        for form in notes.get("readings") or []:
            if isinstance(form, dict):
                add(form.get("text"))
        for sense in notes.get("senses") or []:
            if not isinstance(sense, dict):
                continue
            for value in sense.get("glosses") or []:
                add(value)
            for value in sense.get("parts_of_speech") or []:
                add(value)
            for value in sense.get("tags") or []:
                add(value)
        for kanji in notes.get("kanji") or []:
            if not isinstance(kanji, dict):
                continue
            add(kanji.get("literal"))
            for value in kanji.get("meanings") or []:
                add(value)
            for value in kanji.get("on_readings") or []:
                add(value)
            for value in kanji.get("kun_readings") or []:
                add(value)
        for example in notes.get("dictionary_examples") or []:
            if not isinstance(example, dict):
                continue
            add(example.get("japanese"))
            translations = example.get("translations")
            if isinstance(translations, dict):
                for value in translations.values():
                    add(value)

    for source in word.get("sources") or []:
        if not isinstance(source, dict):
            continue
        add(source.get("title"))
        add(source.get("artist"))
        add(source.get("album"))
    for example in word.get("examples") or []:
        if not isinstance(example, dict):
            continue
        add(example.get("source_title"))
        add(example.get("source_artist"))
        add(example.get("source_album"))
        add(example.get("matched_text"))
        add(example.get("translation_zh"))
        add(example.get("usage_note_zh"))

    return list(dict.fromkeys(terms))[:100]


def _source_index_entry(source: dict[str, Any]) -> dict[str, Any]:
    lines = [line for line in source.get("lines") or [] if isinstance(line, dict)]
    words = sorted({
        match.get("word")
        for line in lines
        for match in line.get("matches") or []
        if isinstance(match, dict) and match.get("word")
    })
    return {
        "source_key": source_document_key(source),
        "source_type": source.get("source_type"),
        "source_title": source.get("source_title"),
        "source_artist": source.get("source_artist"),
        "source_album": source.get("source_album"),
        "source_file": source.get("source_file"),
        "episode": source.get("episode"),
        "token_count": source.get("token_count"),
        "line_count": len(lines),
        "match_count": sum(len(line.get("matches") or []) for line in lines),
        "words": words,
    }


def source_document_key(source: dict[str, Any]) -> str:
    payload = {
        "source_type": source.get("source_type"),
        "source_title": source.get("source_title"),
        "source_artist": source.get("source_artist"),
        "source_album": source.get("source_album"),
        "source_file": source.get("source_file"),
        "episode": source.get("episode"),
    }
    return hashlib.blake2s(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
        digest_size=10,
    ).hexdigest()


def _export_words(
    analysis: CorpusAnalysis,
    *,
    level: int | None,
    lexical_index: LexicalResourceIndex | None = None,
    include_zero_count_words: bool = True,
) -> list[WordStats]:
    words_by_surface = {
        surface: _copy_word_stats(stats)
        for surface, stats in analysis.word_stats.items()
    }
    if include_zero_count_words:
        for entry in analysis.jlpt_words.by_surface.values():
            if level is not None and entry.level != level:
                continue
            words_by_surface.setdefault(entry.surface, WordStats(entry=entry))
    if level is None and lexical_index:
        for surface, stats in analysis.candidate_word_stats.items():
            if surface in analysis.word_stats or stats.count <= 0:
                continue
            if lexical_index.has_jmdict_entry(stats.entry.surface, stats.display_reading):
                canonical_surface = lexical_index.canonical_surface(
                    stats.entry.surface,
                    stats.display_reading,
                )
                candidate = _copy_word_stats(
                    stats,
                    entry=WordEntry(
                        surface=canonical_surface,
                        reading=stats.display_reading,
                        level=0,
                    ),
                )
                existing = words_by_surface.get(canonical_surface)
                if existing:
                    _merge_word_stats(existing, candidate)
                else:
                    words_by_surface[canonical_surface] = candidate
    words = list(words_by_surface.values())
    if level is not None:
        words = [word for word in words if word.entry.level == level]
    words.sort(key=lambda item: (-item.count, _level_sort_value(item), item.entry.surface))
    return words


def _lexical_target_words(
    analysis: CorpusAnalysis,
    *,
    level: int | None,
    include_zero_count_words: bool = True,
) -> list[WordStats]:
    targets = _export_words(
        analysis,
        level=level,
        include_zero_count_words=include_zero_count_words,
    )
    if level is None:
        seen = {word.entry.surface for word in targets}
        targets.extend(
            stats
            for surface, stats in analysis.candidate_word_stats.items()
            if surface not in seen and stats.count > 0
        )
    return targets


def _level_sort_value(word: WordStats) -> int:
    return word.entry.level if word.entry.level > 0 else 9


def _copy_word_stats(stats: WordStats, *, entry: WordEntry | None = None) -> WordStats:
    return WordStats(
        entry=entry or stats.entry,
        count=stats.count,
        sources=stats.sources.copy(),
        source_type_counts=stats.source_type_counts.copy(),
        readings=stats.readings.copy(),
        examples=list(stats.examples),
    )


def _merge_word_stats(target: WordStats, source: WordStats) -> None:
    target.count += source.count
    target.sources.update(source.sources)
    target.source_type_counts.update(source.source_type_counts)
    target.readings.update(source.readings)
    seen = {example.sentence for example in target.examples}
    for example in source.examples:
        if example.sentence in seen:
            continue
        seen.add(example.sentence)
        target.examples.append(example)


def _word_to_dict(
    word: WordStats,
    *,
    examples_per_word: int,
    zh_glossary: ChineseGlossary | None,
    lexical_index: LexicalResourceIndex | None,
) -> dict[str, Any]:
    notes = None
    if lexical_index:
        notes = lexical_index.notes_for(
            word.entry.surface,
            word.display_reading,
            meaning_hint=word.entry.meaning,
        )
    meaning = word.entry.meaning or _meaning_from_lexical_notes(notes)
    payload = {
        "word": word.entry.surface,
        "reading": word.display_reading,
        "level": f"N{word.entry.level}" if word.entry.level > 0 else None,
        "level_number": word.entry.level if word.entry.level > 0 else None,
        "meaning": meaning,
        "meaning_zh": _meaning_zh(word, zh_glossary),
        "count": word.count,
        "source_type_counts": dict(word.source_type_counts),
        "subtitle_count": word.source_type_counts.get("subtitle", 0),
        "lyrics_count": word.source_type_counts.get("lyrics", 0),
        "text_count": word.source_type_counts.get("text", 0),
        "sources": [
            {"title": title, "count": count}
            for title, count in word.sources.most_common()
        ],
        "examples": [
            _example_to_dict(example)
            for example in _select_examples(word.examples, limit=examples_per_word)
        ],
    }
    if notes:
        payload["lexical_notes"] = notes
    return payload


def _meaning_from_lexical_notes(notes: dict[str, object] | None) -> str | None:
    if not notes:
        return None
    glosses: list[str] = []
    for sense in notes.get("senses", []):
        if not isinstance(sense, dict):
            continue
        for gloss in sense.get("glosses", []):
            if isinstance(gloss, str) and gloss:
                glosses.append(gloss)
            if len(glosses) >= 3:
                break
        if len(glosses) >= 3:
            break
    return "; ".join(glosses) if glosses else None


def _word_source_coverage(
    analysis: CorpusAnalysis,
    *,
    word_payloads: list[dict[str, Any]],
    lexical_index: LexicalResourceIndex | None,
) -> dict[str, int]:
    corpus_candidates = [
        stats for stats in analysis.candidate_word_stats.values() if stats.count > 0
    ]
    corpus_jmdict_matches = 0
    if lexical_index:
        corpus_jmdict_matches = sum(
            1
            for stats in corpus_candidates
            if lexical_index.has_jmdict_entry(stats.entry.surface, stats.display_reading)
        )
    return {
        "corpus_candidate_word_count": len(corpus_candidates),
        "corpus_jmdict_match_count": corpus_jmdict_matches,
        "corpus_unmatched_word_count": max(len(corpus_candidates) - corpus_jmdict_matches, 0),
        "exported_word_count": len(word_payloads),
        "exported_jmdict_word_count": sum(
            1 for word in word_payloads if word.get("lexical_notes", {}).get("senses")
        ),
        "exported_zh_meaning_word_count": sum(1 for word in word_payloads if word.get("meaning_zh")),
        "exported_english_only_word_count": sum(
            1
            for word in word_payloads
            if word.get("meaning") and not word.get("meaning_zh")
        ),
    }


def _select_examples(examples: list[WordExample], *, limit: int) -> list[WordExample]:
    remaining = list(examples)
    selected: list[WordExample] = []
    selected_sources: set[tuple[str, str]] = set()
    selected_sentences: set[str] = set()
    while remaining and len(selected) < limit:
        diverse_pool = [
            example
            for example in remaining
            if (example.source_type, example.source_title) not in selected_sources
            and _example_duplicate_key(example) not in selected_sentences
        ]
        unique_pool = [
            example
            for example in remaining
            if _example_duplicate_key(example) not in selected_sentences
        ]
        pool = diverse_pool or unique_pool or remaining
        best = max(pool, key=_example_selection_key)
        selected.append(best)
        selected_sources.add((best.source_type, best.source_title))
        best_key = _example_duplicate_key(best)
        selected_sentences.add(best_key)
        remaining = [
            example
            for example in remaining
            if example is not best and _example_duplicate_key(example) != best_key
        ]
    return selected


def _example_duplicate_key(example: WordExample) -> str:
    return re.sub(r"\s+", "", example.sentence.strip())


def _example_selection_key(example: WordExample) -> tuple[float, int]:
    return (_example_quality_score(example), _stable_example_rank(example))


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


def _stable_example_rank(example: WordExample) -> int:
    payload = {
        "source_type": example.source_type,
        "source_title": example.source_title,
        "source_file": example.subtitle_file,
        "episode": example.episode,
        "start_ms": example.start_ms,
        "matched_text": example.matched_text,
        "sentence": example.sentence,
    }
    digest = hashlib.blake2s(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
        digest_size=8,
    ).digest()
    return int.from_bytes(digest, byteorder="big")


def _meaning_zh(word: WordStats, zh_glossary: ChineseGlossary | None) -> str | None:
    if zh_glossary:
        meaning = zh_glossary.lookup(word.entry.surface, word.display_reading)
        if meaning:
            return meaning
    return word.entry.meaning_zh


def _example_to_dict(example: WordExample) -> dict[str, Any]:
    return {
        "sentence": example.sentence,
        "source_type": example.source_type,
        "source_title": example.source_title,
        "source_artist": example.source_artist,
        "source_album": example.source_album,
        "subtitle_file": example.subtitle_file,
        "matched_text": example.matched_text,
        "episode": example.episode,
        "start_ms": example.start_ms,
        "end_ms": example.end_ms,
        "context_before": example.context_before,
        "context_after": example.context_after,
        "show_context": {
            "summary": example.show_summary,
            "characters": example.show_characters,
        },
        "scene_description": example.scene_description,
        "translation_zh": None,
        "usage_note_zh": None,
        "reference": {
            "source_title": example.source_title,
            "source_artist": example.source_artist,
            "source_album": example.source_album,
            "source_type": example.source_type,
            "source_file": example.subtitle_file,
            "episode": example.episode,
            "start_ms": example.start_ms,
            "end_ms": example.end_ms,
        },
    }


def _source_document_to_dict(
    document: SourceDocument,
    *,
    exported_words: set[str],
) -> dict[str, Any]:
    payload = {
        "source_type": document.source_type,
        "source_title": document.source_title,
        "source_artist": document.source_artist,
        "source_album": document.source_album,
        "source_file": document.source_file,
        "episode": document.episode,
        "token_count": document.token_count,
        "lines": [
            _source_line_to_dict(line, exported_words=exported_words)
            for line in document.lines
        ],
    }
    payload["source_key"] = source_document_key(payload)
    return payload


def _source_line_to_dict(line: SourceLine, *, exported_words: set[str]) -> dict[str, Any]:
    return {
        "text": line.text,
        "start_ms": line.start_ms,
        "end_ms": line.end_ms,
        "matches": [
            _source_line_match_to_dict(match)
            for match in line.matches
            if match.word in exported_words
        ],
    }


def _source_line_match_to_dict(match: SourceLineMatch) -> dict[str, Any]:
    return {
        "word": match.word,
        "matched_text": match.matched_text,
        "reading": match.reading,
        "level": match.level,
        "start": match.start,
        "end": match.end,
    }
