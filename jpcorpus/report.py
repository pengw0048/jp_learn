from __future__ import annotations

from datetime import datetime

from .analysis import CorpusAnalysis
from .i18n import Translator


def build_markdown_report(
    analysis: CorpusAnalysis,
    *,
    target_level: int = 3,
    top: int = 50,
    language: str = "zh",
    examples_per_word: int = 2,
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
        "| {word} | {reading} | {meaning} | {count} | {sources} | {example} |".format(
            word=tr.t("report.col.word"),
            reading=tr.t("report.col.reading"),
            meaning=tr.t("report.col.meaning"),
            count=tr.t("report.col.count"),
            sources=tr.t("report.col.sources"),
            example=tr.t("report.col.example"),
        ),
        "|---|---|---|---:|---|---|",
    ]
    target_words = analysis.top_words(level=target_level, limit=top)
    for stats in target_words:
        sources = "、".join(source for source, _ in stats.sources.most_common(3))
        lines.append(
            "| {word} | {reading} | {meaning} | {count} | {sources} | {example} |".format(
                word=_escape(stats.entry.surface),
                reading=_escape(stats.display_reading),
                meaning=_escape(stats.entry.meaning or ""),
                count=stats.count,
                sources=_escape(sources),
                example=_escape(stats.example_sentence or ""),
            )
        )

    lines.extend(["", f"## {tr.t('report.word_examples', level=target_level)}", ""])
    for stats in target_words:
        lines.extend(
            [
                f"### {_escape_heading(stats.entry.surface)}（{_escape_heading(stats.display_reading)}）",
                "",
                f"- {tr.t('report.col.meaning')}: {_escape(stats.entry.meaning or '')}",
                f"- {tr.t('report.col.count')}: {stats.count:,}",
                f"- {tr.t('report.col.sources')}: {_escape('、'.join(source for source, _ in stats.sources.most_common(3)))}",
                "",
            ]
        )
        for index, example in enumerate(stats.examples[:examples_per_word], start=1):
            lines.append(f"{index}. {_escape(example.sentence)}")
            lines.append(f"   {tr.t('report.col.sources')}: {_escape(example.source_title)}")
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
                meaning=_escape(stats.entry.meaning or ""),
            )
        )

    return "\n".join(lines) + "\n"


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _escape_heading(value: str) -> str:
    return value.replace("\n", " ").strip()
