from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from .jlpt import JLPTWords
from .lyrics import parse_lyrics
from .models import LyricFile, SubtitleFile, SubtitleLine, TextFile, Token, WordEntry
from .subtitle import parse_subtitle
from .texts import parse_text
from .tokenize import JapaneseTokenizer


EXCLUDED_POS = {"助詞", "助動詞", "補助記号", "代名詞", "接続詞", "接頭辞", "接尾辞", "感動詞", "連体詞"}
KATAKANA_EXTENSION_MARKS = {"ー", "ヽ", "ヾ"}
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
    "こと",
    "もの",
    "よう",
    "ため",
    "はず",
    "わけ",
    "つもり",
    "お",
    "ご",
    "さん",
    "ちゃん",
    "くん",
    "たち",
    "うん",
    "ああ",
    "あ",
    "え",
    "ん",
    "あっ",
    "まあ",
}


@dataclass
class WordExample:
    sentence: str
    source_title: str
    subtitle_file: str
    matched_text: str
    source_type: str = "subtitle"
    source_artist: str | None = None
    source_album: str | None = None
    episode: int | None = None
    start_ms: int | None = None
    end_ms: int | None = None
    context_before: list[str] = field(default_factory=list)
    context_after: list[str] = field(default_factory=list)
    show_summary: str | None = None
    show_characters: list[str] = field(default_factory=list)
    scene_description: str | None = None


@dataclass
class SourceLineMatch:
    word: str
    matched_text: str
    reading: str | None = None
    level: int | None = None
    start: int | None = None
    end: int | None = None


@dataclass
class SourceLine:
    text: str
    start_ms: int | None = None
    end_ms: int | None = None
    matches: list[SourceLineMatch] = field(default_factory=list)


@dataclass
class SourceDocument:
    source_type: str
    source_title: str
    source_file: str
    source_artist: str | None = None
    source_album: str | None = None
    episode: int | None = None
    token_count: int = 0
    lines: list[SourceLine] = field(default_factory=list)


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
    text_file_count: int
    total_tokens: int
    unique_token_count: int
    word_stats: dict[str, WordStats]
    candidate_word_stats: dict[str, WordStats]
    show_stats: dict[str, ShowStats]
    seen_by_level: dict[int, set[str]]
    jlpt_words: JLPTWords
    music_track_count: int = 0
    lyric_file_count: int = 0
    source_type_counts: Counter[str] = field(default_factory=Counter)
    source_documents: list[SourceDocument] = field(default_factory=list)

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
        text_files=[],
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
    text_files: list[TextFile] | None = None,
    jlpt_words: JLPTWords,
    max_examples_per_word: int = 3,
    context_lines: int = 2,
    context_min_chars: int = 0,
    context_max_lines: int | None = None,
) -> CorpusAnalysis:
    tokenizer = JapaneseTokenizer()
    word_stats: dict[str, WordStats] = {}
    candidate_word_stats: dict[str, WordStats] = {}
    show_stats: dict[str, ShowStats] = {}
    seen_by_level: dict[int, set[str]] = defaultdict(set)
    unique_tokens: set[str] = set()
    source_type_counts: Counter[str] = Counter()
    source_documents: list[SourceDocument] = []
    total_tokens = 0
    text_files = text_files or []

    def consume_lines(
        *,
        source_type: str,
        source_title: str,
        source_file: str,
        lines: list[SubtitleLine],
        source_artist: str | None = None,
        source_album: str | None = None,
        episode: int | None = None,
        show_summary: str | None = None,
        show_characters: list[str] | None = None,
    ) -> None:
        nonlocal total_tokens
        source = show_stats.setdefault(source_title, ShowStats(title=source_title))
        source.file_count += 1
        character_aliases = build_character_aliases(show_characters or [], tokenizer)
        if source_type == "subtitle":
            lines = strip_subtitle_parentheticals(lines)
        document = SourceDocument(
            source_type=source_type,
            source_title=source_title,
            source_file=source_file,
            source_artist=source_artist,
            source_album=source_album,
            episode=episode,
        )
        for line_index, line in enumerate(lines):
            tokens = tokenizer.tokenize(line.text)
            document.token_count += len(tokens)
            line_matches: list[SourceLineMatch] = []
            for token in tokens:
                total_tokens += 1
                source_type_counts[source_type] += 1
                source.total_tokens += 1
                unique_tokens.add(token.base)
                if not is_study_candidate(token.base, token.pos, token.pos_detail):
                    continue
                reading = to_hiragana(token.reading) if token.reading else None
                entry = jlpt_words.lookup(token.base, token.surface)
                if entry is None and can_lookup_by_reading(token):
                    entry = jlpt_words.lookup_reading(token.base, reading)
                candidate_entry = entry or WordEntry(
                    surface=token.base,
                    reading=reading,
                    level=0,
                )
                if is_character_name_token(token, character_aliases, candidate_entry.surface):
                    continue
                if is_embedded_katakana_match(line.text, token, candidate_entry):
                    continue
                line_matches.append(
                    SourceLineMatch(
                        word=candidate_entry.surface,
                        matched_text=token.surface,
                        reading=reading,
                        level=candidate_entry.level if candidate_entry.level > 0 else None,
                        start=token.start,
                        end=token.end,
                    )
                )
                stats = candidate_word_stats.setdefault(
                    candidate_entry.surface,
                    WordStats(entry=candidate_entry),
                )
                record_word_stats(
                    stats,
                    token=token,
                    line=line,
                    lines=lines,
                    line_index=line_index,
                    source_type=source_type,
                    source_title=source_title,
                    source_file=source_file,
                    source_artist=source_artist,
                    source_album=source_album,
                    episode=episode,
                    show_summary=show_summary,
                    show_characters=show_characters or [],
                    context_lines=context_lines,
                    context_min_chars=context_min_chars,
                    context_max_lines=context_max_lines,
                    max_examples_per_word=max_examples_per_word,
                )
                if entry is None:
                    continue
                seen_by_level[entry.level].add(entry.surface)
                source.jlpt_counts[entry.level] += 1
                source.unique_words.add(entry.surface)
                if stats.entry.surface == entry.surface:
                    word_stats[entry.surface] = stats
                else:
                    jlpt_stats = word_stats.setdefault(entry.surface, WordStats(entry=entry))
                    record_word_stats(
                        jlpt_stats,
                        token=token,
                        line=line,
                        lines=lines,
                        line_index=line_index,
                        source_type=source_type,
                        source_title=source_title,
                        source_file=source_file,
                        source_artist=source_artist,
                        source_album=source_album,
                        episode=episode,
                        show_summary=show_summary,
                        show_characters=show_characters or [],
                        context_lines=context_lines,
                        context_min_chars=context_min_chars,
                        context_max_lines=context_max_lines,
                        max_examples_per_word=max_examples_per_word,
                    )
            document.lines.append(
                SourceLine(
                    text=line.text,
                    start_ms=line.start_ms,
                    end_ms=line.end_ms,
                    matches=line_matches,
                )
            )
        source_documents.append(document)

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
            source_artist=lyric_file.artist,
            source_album=lyric_file.album_title,
            lines=parse_lyrics(lyric_file.path),
        )

    for text_file in text_files:
        if not text_file.path.exists():
            continue
        consume_lines(
            source_type="text",
            source_title=text_file.title,
            source_file=text_file.name,
            lines=parse_text(text_file.path),
            source_artist=text_file.author,
        )

    subtitle_show_count = len({file.bangumi_id for file in subtitle_files if file.path.exists()})
    existing_lyric_files = [file for file in lyric_files if file.path.exists()]
    existing_text_files = [file for file in text_files if file.path.exists()]
    return CorpusAnalysis(
        watched_show_count=watched_show_count,
        subtitle_show_count=subtitle_show_count,
        subtitle_file_count=len([file for file in subtitle_files if file.path.exists()]),
        text_file_count=len(existing_text_files),
        total_tokens=total_tokens,
        unique_token_count=len(unique_tokens),
        word_stats=word_stats,
        candidate_word_stats=candidate_word_stats,
        show_stats=show_stats,
        seen_by_level=dict(seen_by_level),
        jlpt_words=jlpt_words,
        music_track_count=music_track_count,
        lyric_file_count=len(existing_lyric_files),
        source_type_counts=source_type_counts,
        source_documents=source_documents,
    )


def record_word_stats(
    stats: WordStats,
    *,
    token: Token,
    line: SubtitleLine,
    lines: list[SubtitleLine],
    line_index: int,
    source_type: str,
    source_title: str,
    source_file: str,
    source_artist: str | None,
    source_album: str | None,
    episode: int | None,
    show_summary: str | None,
    show_characters: list[str],
    context_lines: int,
    context_min_chars: int,
    context_max_lines: int | None,
    max_examples_per_word: int,
) -> None:
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
            source_artist=source_artist,
            source_album=source_album,
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
            show_characters=show_characters,
        ),
        limit=max_examples_per_word,
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


def is_study_candidate(base: str, pos: str | None, pos_detail: str | None = None) -> bool:
    if pos in EXCLUDED_POS:
        return False
    if pos_detail and "固有名詞" in pos_detail:
        return False
    if base in STUDY_STOPWORDS:
        return False
    return True


def can_lookup_by_reading(token: Token) -> bool:
    return not (has_cjk_text(token.surface) or has_cjk_text(token.base))


def build_character_aliases(character_names: list[str], tokenizer: JapaneseTokenizer) -> set[str]:
    aliases: set[str] = set()
    for name in character_names:
        for part in character_name_parts(name):
            add_character_alias(aliases, part)
            if len(part) >= 4 and is_cjk_text(part[-2:]):
                add_character_alias(aliases, part[-2:])
            for token in tokenizer.tokenize(part):
                if is_character_name_part_token(token):
                    add_character_alias(aliases, token.surface)
                    add_character_alias(aliases, token.base)
    return aliases


def character_name_parts(name: str) -> list[str]:
    return [
        part
        for part in re.split(r"[\s　・･/／、，,（）()\[\]【】]+", str(name))
        if part and has_japanese_text(part)
    ]


def is_character_name_part_token(token: Token) -> bool:
    if token.pos_detail and "固有名詞" in token.pos_detail:
        return True
    return len(token.surface) >= 2 and has_japanese_text(token.surface)


def add_character_alias(aliases: set[str], value: str) -> None:
    alias = value.strip()
    if not alias or alias in STUDY_STOPWORDS:
        return
    if len(alias) == 1 and not has_japanese_text(alias):
        return
    aliases.add(alias)


def strip_subtitle_parentheticals(lines: list[SubtitleLine]) -> list[SubtitleLine]:
    cleaned = []
    for line in lines:
        text = strip_parenthetical_text(line.text)
        if text:
            cleaned.append(SubtitleLine(text=text, start_ms=line.start_ms, end_ms=line.end_ms))
    return cleaned


def strip_parenthetical_text(text: str) -> str:
    cleaned_lines = []
    for line in str(text or "").splitlines():
        stripped = normalize_space(strip_parenthetical_fragments(line))
        if stripped:
            cleaned_lines.append(stripped)
    return "\n".join(cleaned_lines)


def strip_parenthetical_fragments(text: str) -> str:
    pairs = {"(": ")", "（": "）"}
    close_to_open = {close: open_char for open_char, close in pairs.items()}
    output = []
    stack: list[str] = []
    for char in str(text or ""):
        if char in pairs:
            stack.append(pairs[char])
            continue
        if stack:
            if char == stack[-1]:
                stack.pop()
            continue
        if char in close_to_open:
            continue
        output.append(char)
    return "".join(output)


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def is_character_name_token(token: Token, aliases: set[str], *resolved_surfaces: str | None) -> bool:
    if not aliases:
        return False
    return any(
        value in aliases
        for value in (token.surface, token.base, *resolved_surfaces)
        if value
    )


def has_japanese_text(value: str) -> bool:
    return bool(re.search(r"[\u3040-\u30ff\u3400-\u9fff々〆ヵヶ]", value))


def has_cjk_text(value: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff々〆]", value))


def is_cjk_text(value: str) -> bool:
    return bool(value) and all("\u3400" <= char <= "\u9fff" or char in {"々"} for char in value)


def is_embedded_katakana_match(text: str, token: Token, entry: WordEntry) -> bool:
    if token.start is None or token.end is None:
        return False
    if not _is_katakana_word(token.surface) or not _is_katakana_word(entry.surface):
        return False

    left = text[token.start - 1] if token.start > 0 else ""
    right = text[token.end] if token.end < len(text) else ""
    return _is_katakana_word_char(left) or _is_katakana_word_char(right)


def _is_katakana_word(value: str) -> bool:
    return bool(value) and all(_is_katakana_word_char(char) for char in value)


def _is_katakana_word_char(char: str) -> bool:
    if char in KATAKANA_EXTENSION_MARKS:
        return True
    if len(char) != 1:
        return False
    codepoint = ord(char)
    return 0x30A1 <= codepoint <= 0x30FA


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
