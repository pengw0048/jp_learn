from __future__ import annotations

from datetime import datetime

from .analysis import CorpusAnalysis, WordExample, WordStats
from .i18n import Translator
from .zh_dict import ChineseGlossary


def build_markdown_report(
    analysis: CorpusAnalysis,
    *,
    target_level: int = 3,
    top: int = 50,
    language: str = "zh",
    examples_per_word: int = 2,
    zh_glossary: ChineseGlossary | None = None,
) -> str:
    tr = Translator(language)
    coverage = " / ".join(
        f"N{level}: {analysis.coverage(level):.0%}" for level in range(5, 0, -1)
    )
    lines = [
        f"# {tr.t('report.title')}",
        "",
        f"{tr.t('report.generated_at')}: {datetime.now().isoformat(timespec='seconds')}",
        "",
        tr.t("report.summary"),
        "- "
        + tr.t(
            "report.summary_counts",
            watched=analysis.watched_show_count,
            subtitle_shows=analysis.subtitle_show_count,
            tokens=f"{analysis.total_tokens:,}",
            unique_tokens=f"{analysis.unique_token_count:,}",
        ),
        f"- {tr.t('report.coverage', coverage=coverage)}",
        "",
        f"## {tr.t('report.word_list', level=target_level)}",
        "",
        "| {word} | {reading} | {meaning} | {count} | {example} |".format(
            word=tr.t("report.col.word"),
            reading=tr.t("report.col.reading"),
            meaning=tr.t("report.col.meaning"),
            count=tr.t("report.col.count"),
            example=tr.t("report.col.example"),
        ),
        "|---|---|---|---:|---|",
    ]
    target_words = analysis.top_words(level=target_level, limit=top)
    for stats in target_words:
        lines.append(
            "| {word} | {reading} | {meaning} | {count} | {example} |".format(
                word=_escape(stats.entry.surface),
                reading=_escape(stats.display_reading),
                meaning=_escape(display_meaning(stats, language=language, zh_glossary=zh_glossary)),
                count=stats.count,
                example=_escape(highlight_example(stats.example_sentence or "", stats)),
            )
        )

    lines.extend(["", f"## {tr.t('report.word_examples', level=target_level)}", ""])
    for stats in target_words:
        lines.extend(
            [
                f"### {_escape_heading(stats.entry.surface)}（{_escape_heading(stats.display_reading)}）",
                "",
                f"- {tr.t('report.col.meaning')}: {_escape(display_meaning(stats, language=language, zh_glossary=zh_glossary))}",
                f"- {tr.t('report.col.count')}: {stats.count:,}",
                "",
            ]
        )
        for index, example in enumerate(stats.examples[:examples_per_word], start=1):
            lines.append(f"{index}.")
            lines.extend(format_context_block(example, stats, inline_reference=True))
            if example.scene_description:
                lines.append(f"   {tr.t('report.col.scene')}: {_escape(example.scene_description)}")
            lines.append("")

    lines.extend(
        [
            "",
            f"## {tr.t('report.by_show')}",
            "",
            "| {show} | {files} | {tokens} | {unique} | {hits} |".format(
                show=tr.t("report.col.show"),
                files=tr.t("report.col.subtitle_files"),
                tokens=tr.t("report.col.total_tokens"),
                unique=tr.t("report.col.unique_jlpt"),
                hits=tr.t("report.col.level_hits", level=target_level),
            ),
            "|---|---:|---:|---:|---:|",
        ]
    )
    shows = sorted(
        analysis.show_stats.values(),
        key=lambda show: (-show.jlpt_counts.get(target_level, 0), show.title),
    )
    for show in shows:
        lines.append(
            f"| {_escape(show.title)} | {show.file_count} | {show.total_tokens:,} | "
            f"{len(show.unique_words):,} | {show.jlpt_counts.get(target_level, 0):,} |"
        )

    lines.extend(
        [
            "",
            f"## {tr.t('report.all_top_words')}",
            "",
            "| {word} | {level} | {reading} | {count} | {meaning} |".format(
                word=tr.t("report.col.word"),
                level=tr.t("report.col.level"),
                reading=tr.t("report.col.reading"),
                count=tr.t("report.col.count"),
                meaning=tr.t("report.col.meaning"),
            ),
            "|---|---|---|---:|---|",
        ]
    )
    for stats in analysis.top_words(limit=top):
        lines.append(
            "| {word} | N{level} | {reading} | {count} | {meaning} |".format(
                word=_escape(stats.entry.surface),
                level=stats.entry.level,
                reading=_escape(stats.display_reading),
                count=stats.count,
                meaning=_escape(display_meaning(stats, language=language, zh_glossary=zh_glossary)),
            )
        )

    return "\n".join(lines) + "\n"


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _escape_heading(value: str) -> str:
    return value.replace("\n", " ").strip()


def display_meaning(stats: WordStats, *, language: str, zh_glossary: ChineseGlossary | None) -> str:
    if language == "zh":
        glossary_meaning = (
            zh_glossary.lookup(stats.entry.surface, stats.display_reading)
            if zh_glossary
            else None
        )
        if glossary_meaning:
            return glossary_meaning
        if stats.entry.meaning_zh:
            return stats.entry.meaning_zh
    return stats.entry.meaning or ""


def format_context_block(
    example: WordExample,
    stats: WordStats,
    *,
    inline_reference: bool = False,
) -> list[str]:
    lines: list[str] = []
    if example.context_before:
        before = " / ".join(example.context_before[-2:])
        lines.append(f"   …{_escape(before)}")
    current = _escape(highlight_example(example.sentence, stats, example=example))
    if inline_reference:
        current += f" （{_escape(format_reference(example, brackets=False))}）"
    lines.append(f"   {current}")
    if example.context_after:
        after = " / ".join(example.context_after[:2])
        lines.append(f"   …{_escape(after)}")
    return lines


def highlight_example(sentence: str, stats: WordStats, *, example: WordExample | None = None) -> str:
    candidates = []
    if example and example.matched_text:
        candidates.append(example.matched_text)
    candidates.extend([stats.entry.surface, stats.display_reading])
    for candidate in candidates:
        if candidate and candidate in sentence:
            return sentence.replace(candidate, f"**{candidate}**", 1)
    return sentence


def format_reference(example: WordExample, *, brackets: bool = True) -> str:
    source = f"《{example.source_title}》" if brackets else example.source_title
    parts = [source]
    if example.episode is not None:
        parts.append(f"EP{example.episode:02d}")
    elif example.subtitle_file:
        parts.append(example.subtitle_file)
    if example.start_ms is not None:
        parts.append(format_timestamp(example.start_ms))
    return " ".join(parts)


def format_timestamp(milliseconds: int) -> str:
    seconds = milliseconds // 1000
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"
