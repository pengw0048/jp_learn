from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from .jlpt import JLPTWords
from .lyrics import parse_lyrics
from .models import LyricFile, SubtitleFile, SubtitleLine, WordEntry
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
    source_type: str = "subtitle"
    episode: int | None = None
    start_ms: int | None = None
    end_ms: int | None = None
    context_before: list[str] = field(default_factory=list)
    context_after: list[str] = field(default_factory=list)
    show_summary: str | None = None
    show_characters: list[str] = field(default_factory=list)
    scene_description: str | None = None


@dataclass
class WordStats:
    entry: WordEntry
    count: int = 0
    sources: Counter[str] = field(default_factory=Counter)
    source_type_counts: Counter[str] = field(default_factory=Counter)
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
        if limit <= 0:
            return
        if any(existing.sentence == example.sentence for existing in self.examples):
            return
        if len(self.examples) < limit:
            self.examples.append(example)
            return
        sources = Counter(existing.source_title for existing in self.examples)
        if example.source_title in sources:
            return
        crowded_source = sources.most_common(1)[0][0]
        for index in range(len(self.examples) - 1, -1, -1):
            if self.examples[index].source_title == crowded_source:
                self.examples[index] = example
                return


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
    music_track_count: int = 0
    lyric_file_count: int = 0
    source_type_counts: Counter[str] = field(default_factory=Counter)

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
    context_min_chars: int = 0,
    context_max_lines: int | None = None,
) -> CorpusAnalysis:
    return analyze_media(
        watched_show_count=watched_show_count,
        music_track_count=0,
        subtitle_files=subtitle_files,
        lyric_files=[],
        jlpt_words=jlpt_words,
        max_examples_per_word=max_examples_per_word,
        context_lines=context_lines,
        context_min_chars=context_min_chars,
        context_max_lines=context_max_lines,
    )


def analyze_media(
    *,
    watched_show_count: int,
    music_track_count: int,
    subtitle_files: list[SubtitleFile],
    lyric_files: list[LyricFile],
    jlpt_words: JLPTWords,
    max_examples_per_word: int = 3,
    context_lines: int = 2,
    context_min_chars: int = 0,
    context_max_lines: int | None = None,
) -> CorpusAnalysis:
    tokenizer = JapaneseTokenizer()
    word_stats: dict[str, WordStats] = {}
    show_stats: dict[str, ShowStats] = {}
    seen_by_level: dict[int, set[str]] = defaultdict(set)
    unique_tokens: set[str] = set()
    source_type_counts: Counter[str] = Counter()
    total_tokens = 0

    def consume_lines(
        *,
        source_type: str,
        source_title: str,
        source_file: str,
        lines: list[SubtitleLine],
        episode: int | None = None,
        show_summary: str | None = None,
        show_characters: list[str] | None = None,
    ) -> None:
        nonlocal total_tokens
        source = show_stats.setdefault(source_title, ShowStats(title=source_title))
        source.file_count += 1
        for line_index, line in enumerate(lines):
            tokens = tokenizer.tokenize(line.text)
            for token in tokens:
                total_tokens += 1
                source_type_counts[source_type] += 1
                source.total_tokens += 1
                unique_tokens.add(token.base)
                if not is_study_candidate(token.base, token.pos):
                    continue
                entry = jlpt_words.lookup(token.base, token.surface)
                if entry is None:
                    continue
                seen_by_level[entry.level].add(entry.surface)
                source.jlpt_counts[entry.level] += 1
                source.unique_words.add(entry.surface)
                stats = word_stats.setdefault(entry.surface, WordStats(entry=entry))
                stats.count += 1
                stats.sources[source_title] += 1
                stats.source_type_counts[source_type] += 1
                if token.reading:
                    stats.readings[to_hiragana(token.reading)] += 1
                stats.add_example(
                    WordExample(
                        sentence=line.text,
                        source_title=source_title,
                        subtitle_file=source_file,
                        matched_text=token.surface,
                        source_type=source_type,
                        episode=episode,
                        start_ms=line.start_ms,
                        end_ms=line.end_ms,
                        context_before=collect_context(
                            lines,
                            line_index=line_index,
                            direction="before",
                            preferred_lines=context_lines,
                            min_chars=context_min_chars,
                            max_lines=context_max_lines,
                        ),
                        context_after=collect_context(
                            lines,
                            line_index=line_index,
                            direction="after",
                            preferred_lines=context_lines,
                            min_chars=context_min_chars,
                            max_lines=context_max_lines,
                        ),
                        show_summary=show_summary,
                        show_characters=show_characters or [],
                    ),
                    limit=max_examples_per_word,
                )

    for subtitle_file in subtitle_files:
        if not subtitle_file.path.exists():
            continue
        consume_lines(
            source_type="subtitle",
            source_title=subtitle_file.show_title,
            source_file=subtitle_file.name,
            lines=parse_subtitle(subtitle_file.path),
            episode=subtitle_file.episode,
            show_summary=subtitle_file.show_summary,
            show_characters=subtitle_file.show_characters,
        )

    for lyric_file in lyric_files:
        if not lyric_file.path.exists():
            continue
        consume_lines(
            source_type="lyrics",
            source_title=lyric_file.track_title,
            source_file=lyric_file.path.name,
            lines=parse_lyrics(lyric_file.path),
        )

    subtitle_show_count = len({file.bangumi_id for file in subtitle_files if file.path.exists()})
    existing_lyric_files = [file for file in lyric_files if file.path.exists()]
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
        music_track_count=music_track_count,
        lyric_file_count=len(existing_lyric_files),
        source_type_counts=source_type_counts,
    )


def collect_context(
    subtitle_lines: list[SubtitleLine],
    *,
    line_index: int,
    direction: str,
    preferred_lines: int,
    min_chars: int = 0,
    max_lines: int | None = None,
) -> list[str]:
    if preferred_lines <= 0 and min_chars <= 0:
        return []
    if max_lines is None:
        max_lines = max(preferred_lines, preferred_lines + 6)
    selected = []
    char_count = 0
    if direction == "before":
        indexes = range(line_index - 1, -1, -1)
    elif direction == "after":
        indexes = range(line_index + 1, len(subtitle_lines))
    else:
        raise ValueError(f"Unsupported context direction: {direction}")
    for index in indexes:
        text = subtitle_lines[index].text.strip()
        if not text:
            continue
        selected.append(text)
        char_count += len(text)
        if len(selected) >= preferred_lines and char_count >= min_chars:
            break
        if len(selected) >= max_lines:
            break
    if direction == "before":
        selected.reverse()
    return selected


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
    context_min_chars: int = 0,
    context_max_lines: int | None = None,
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
        context_min_chars=context_min_chars,
        context_max_lines=context_max_lines,
    )
