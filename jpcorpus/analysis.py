from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from .jlpt import JLPTWords
from .models import SubtitleFile, WordEntry
from .subtitle import parse_subtitle
from .tokenize import JapaneseTokenizer


EXCLUDED_POS = {"助詞", "助動詞", "補助記号", "代名詞", "接続詞"}
STUDY_STOPWORDS = {
    "ある",
    "いる",
    "する",
    "なる",
    "ない",
    "これ",
    "それ",
    "あれ",
    "この",
    "その",
    "あの",
    "ここ",
    "そこ",
    "あそこ",
    "どこ",
    "何",
    "はい",
    "いいえ",
    "そう",
    "どう",
    "もう",
    "また",
    "まだ",
    "ずっと",
    "もっと",
    "とても",
    "うん",
    "ああ",
    "まあ",
}


@dataclass
class WordExample:
    sentence: str
    source_title: str
    subtitle_file: str
    matched_text: str
    episode: int | None = None
    start_ms: int | None = None
    end_ms: int | None = None
    context_before: list[str] = field(default_factory=list)
    context_after: list[str] = field(default_factory=list)
    scene_description: str | None = None


@dataclass
class WordStats:
    entry: WordEntry
    count: int = 0
    sources: Counter[str] = field(default_factory=Counter)
    readings: Counter[str] = field(default_factory=Counter)
    examples: list[WordExample] = field(default_factory=list)

    @property
    def display_reading(self) -> str:
        if self.entry.reading:
            return self.entry.reading
        if self.readings:
            return self.readings.most_common(1)[0][0]
        return ""

    @property
    def example_sentence(self) -> str | None:
        return self.examples[0].sentence if self.examples else None

    @property
    def example_source(self) -> str | None:
        return self.examples[0].source_title if self.examples else None

    def add_example(self, example: WordExample, *, limit: int) -> None:
        if len(self.examples) >= limit:
            return
        if any(existing.sentence == example.sentence for existing in self.examples):
            return
        self.examples.append(example)


@dataclass
class ShowStats:
    title: str
    file_count: int = 0
    total_tokens: int = 0
    jlpt_counts: Counter[int] = field(default_factory=Counter)
    unique_words: set[str] = field(default_factory=set)


@dataclass
class CorpusAnalysis:
    watched_show_count: int
    subtitle_show_count: int
    subtitle_file_count: int
    total_tokens: int
    unique_token_count: int
    word_stats: dict[str, WordStats]
    show_stats: dict[str, ShowStats]
    seen_by_level: dict[int, set[str]]
    jlpt_words: JLPTWords

    def top_words(self, *, level: int | None = None, limit: int = 50) -> list[WordStats]:
        words = list(self.word_stats.values())
        if level is not None:
            words = [word for word in words if word.entry.level == level]
        words.sort(key=lambda item: (-item.count, item.entry.level, item.entry.surface))
        return words[:limit]

    def coverage(self, level: int) -> float:
        total = self.jlpt_words.total_by_level(level)
        if total == 0:
            return 0.0
        return len(self.seen_by_level.get(level, set())) / total


def analyze_subtitles(
    *,
    watched_show_count: int,
    subtitle_files: list[SubtitleFile],
    jlpt_words: JLPTWords,
    max_examples_per_word: int = 3,
    context_lines: int = 2,
) -> CorpusAnalysis:
    tokenizer = JapaneseTokenizer()
    word_stats: dict[str, WordStats] = {}
    show_stats: dict[str, ShowStats] = {}
    seen_by_level: dict[int, set[str]] = defaultdict(set)
    unique_tokens: set[str] = set()
    total_tokens = 0

    for subtitle_file in subtitle_files:
        if not subtitle_file.path.exists():
            continue
        show = show_stats.setdefault(
            subtitle_file.show_title,
            ShowStats(title=subtitle_file.show_title),
        )
        show.file_count += 1
        subtitle_lines = parse_subtitle(subtitle_file.path)
        for line_index, line in enumerate(subtitle_lines):
            tokens = tokenizer.tokenize(line.text)
            for token in tokens:
                total_tokens += 1
                show.total_tokens += 1
                unique_tokens.add(token.base)
                if not is_study_candidate(token.base, token.pos):
                    continue
                entry = jlpt_words.lookup(token.base, token.surface)
                if entry is None:
                    continue
                seen_by_level[entry.level].add(entry.surface)
                show.jlpt_counts[entry.level] += 1
                show.unique_words.add(entry.surface)
                stats = word_stats.setdefault(entry.surface, WordStats(entry=entry))
                stats.count += 1
                stats.sources[subtitle_file.show_title] += 1
                if token.reading:
                    stats.readings[to_hiragana(token.reading)] += 1
                stats.add_example(
                    WordExample(
                        sentence=line.text,
                        source_title=subtitle_file.show_title,
                        subtitle_file=subtitle_file.name,
                        matched_text=token.surface,
                        episode=subtitle_file.episode,
                        start_ms=line.start_ms,
                        end_ms=line.end_ms,
                        context_before=[
                            context_line.text
                            for context_line in subtitle_lines[
                                max(0, line_index - context_lines) : line_index
                            ]
                        ],
                        context_after=[
                            context_line.text
                            for context_line in subtitle_lines[
                                line_index + 1 : line_index + 1 + context_lines
                            ]
                        ],
                    ),
                    limit=max_examples_per_word,
                )

    subtitle_show_count = len({file.bangumi_id for file in subtitle_files if file.path.exists()})
    return CorpusAnalysis(
        watched_show_count=watched_show_count,
        subtitle_show_count=subtitle_show_count,
        subtitle_file_count=len([file for file in subtitle_files if file.path.exists()]),
        total_tokens=total_tokens,
        unique_token_count=len(unique_tokens),
        word_stats=word_stats,
        show_stats=show_stats,
        seen_by_level=dict(seen_by_level),
        jlpt_words=jlpt_words,
    )


def is_study_candidate(base: str, pos: str | None) -> bool:
    if pos in EXCLUDED_POS:
        return False
    if base in STUDY_STOPWORDS:
        return False
    return True


def to_hiragana(value: str) -> str:
    chars = []
    for char in value:
        codepoint = ord(char)
        if 0x30A1 <= codepoint <= 0x30F6:
            chars.append(chr(codepoint - 0x60))
        else:
            chars.append(char)
    return "".join(chars)


def analyze_paths(
    *,
    paths: list[Path],
    jlpt_words: JLPTWords,
    title: str = "Local subtitles",
    max_examples_per_word: int = 3,
    context_lines: int = 2,
) -> CorpusAnalysis:
    subtitle_files = [
        SubtitleFile(bangumi_id=index + 1, show_title=title, path=path, name=path.name)
        for index, path in enumerate(paths)
    ]
    return analyze_subtitles(
        watched_show_count=1 if paths else 0,
        subtitle_files=subtitle_files,
        jlpt_words=jlpt_words,
        max_examples_per_word=max_examples_per_word,
        context_lines=context_lines,
    )
