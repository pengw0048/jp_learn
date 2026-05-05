from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SUPPORTED_LANGUAGES = ("zh", "en")


MESSAGES: dict[str, dict[str, str]] = {
    "zh": {
        "report.title": "个人日语语料单词表",
        "report.generated_at": "生成时间",
        "report.summary": "总览：",
        "report.summary_counts": "{watched} 部看过 -> {subtitle_shows} 部有字幕 + {lyric_files} 个歌词文件 -> {tokens} 个词形 -> {unique_tokens} 个独特词形",
        "report.coverage": "已覆盖 JLPT {coverage}",
        "report.word_list": "N{level} 单词表",
        "report.word_examples": "N{level} 单词例句",
        "report.by_show": "按作品的覆盖",
        "report.all_top_words": "全部高频 JLPT 词",
        "report.col.word": "词",
        "report.col.reading": "假名",
        "report.col.count": "频次",
        "report.col.sources": "来自作品",
        "report.col.reference": "引用",
        "report.col.context_before": "前文",
        "report.col.context_after": "后文",
        "report.col.scene": "场景",
        "report.col.example": "例句",
        "report.col.show": "作品",
        "report.col.subtitle_files": "文件",
        "report.col.total_tokens": "总词形",
        "report.col.unique_jlpt": "JLPT 独特词",
        "report.col.level_hits": "N{level} 出现次数",
        "report.col.level": "JLPT",
        "report.col.meaning": "释义",
    },
    "en": {
        "report.title": "Personal Japanese Corpus Word List",
        "report.generated_at": "Generated at",
        "report.summary": "Summary:",
        "report.summary_counts": "{watched} watched shows -> {subtitle_shows} with subtitles + {lyric_files} lyric files -> {tokens} tokens -> {unique_tokens} unique tokens",
        "report.coverage": "JLPT coverage: {coverage}",
        "report.word_list": "N{level} Word List",
        "report.word_examples": "N{level} Word Examples",
        "report.by_show": "Coverage by show",
        "report.all_top_words": "Top JLPT words overall",
        "report.col.word": "Word",
        "report.col.reading": "Reading",
        "report.col.count": "Count",
        "report.col.sources": "Sources",
        "report.col.reference": "Reference",
        "report.col.context_before": "Before",
        "report.col.context_after": "After",
        "report.col.scene": "Scene",
        "report.col.example": "Example",
        "report.col.show": "Show",
        "report.col.subtitle_files": "Files",
        "report.col.total_tokens": "Total tokens",
        "report.col.unique_jlpt": "Unique JLPT words",
        "report.col.level_hits": "N{level} hits",
        "report.col.level": "JLPT",
        "report.col.meaning": "Meaning",
    },
}


@dataclass(frozen=True)
class Translator:
    language: str = "zh"

    def __post_init__(self) -> None:
        if self.language not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Unsupported language: {self.language}. Supported: {', '.join(SUPPORTED_LANGUAGES)}"
            )

    def t(self, key: str, **values: Any) -> str:
        template = MESSAGES.get(self.language, {}).get(key) or MESSAGES["en"].get(key)
        if template is None:
            return key
        return template.format(**values)
