from pathlib import Path

from jpcorpus.analysis import (
    WordExample,
    WordStats,
    analyze_media,
    analyze_paths,
    collect_context,
    is_study_candidate,
    to_hiragana,
)
from jpcorpus.anki_export import export_anki_deck
from jpcorpus.corpus_export import _select_examples, analysis_to_dict, write_corpus_json
from jpcorpus.jlpt import load_jlpt_words, parse_level, write_sample_jlpt
from jpcorpus.models import LyricFile, SubtitleFile, SubtitleLine, WordEntry
from jpcorpus.report import build_markdown_report
from jpcorpus.report import format_reference, format_timestamp
from jpcorpus.subtitle import clean_subtitle_text
from jpcorpus.zh_dict import ChineseGlossary, clean_gloss


def test_report_from_local_srt(tmp_path: Path):
    jlpt_path = tmp_path / "jlpt.json"
    write_sample_jlpt(jlpt_path)
    subtitle = tmp_path / "sample.srt"
    subtitle.write_text(
        "1\n00:00:01,000 --> 00:00:03,000\n今日は学校へ行く。\n\n"
        "2\n00:00:04,000 --> 00:00:06,000\n私は約束を見る。\n\n"
        "3\n00:00:07,000 --> 00:00:09,000\n微妙な気持ちだ。\n\n"
        "4\n00:00:10,000 --> 00:00:12,000\n明日も行く。\n",
        encoding="utf-8",
    )

    analysis = analyze_paths(paths=[subtitle], jlpt_words=load_jlpt_words(jlpt_path), context_lines=1)
    report = build_markdown_report(
        analysis,
        target_level=3,
        top=10,
        zh_glossary=ChineseGlossary({"微妙": "微妙，细微；难以形容"}),
    )
    english_report = build_markdown_report(analysis, target_level=3, top=10, language="en")

    assert "个人日语语料单词表" in report
    assert "N3 单词表" in report
    assert "N3 单词例句" in report
    assert "私は約束を見る。" in report
    assert "明日も行く。" in report
    assert "微妙，细微" in report
    assert "<br>" not in report
    assert (
        "…私は約束を見る。 **微妙**な気持ちだ。 "
        "…明日も行く。 （Local subtitles sample.srt 00:07）"
    ) in report
    assert "1. …私は約束を見る。" not in report
    assert "Personal Japanese Corpus Word List" in english_report
    assert "微妙" in report
    assert analysis.total_tokens > 0


def test_export_anki_deck(tmp_path: Path):
    jlpt_path = tmp_path / "jlpt.json"
    write_sample_jlpt(jlpt_path)
    subtitle = tmp_path / "sample.srt"
    subtitle.write_text(
        "1\n00:00:01,000 --> 00:00:03,000\n私は約束を見る。\n",
        encoding="utf-8",
    )
    analysis = analyze_paths(paths=[subtitle], jlpt_words=load_jlpt_words(jlpt_path))
    output = tmp_path / "deck.apkg"

    export_anki_deck(analysis, output=output, level=4, limit=10)

    assert output.exists()
    assert output.stat().st_size > 0


def test_export_corpus_json(tmp_path: Path):
    jlpt_path = tmp_path / "jlpt.json"
    write_sample_jlpt(jlpt_path)
    subtitle = tmp_path / "sample.srt"
    subtitle.write_text(
        "1\n00:00:01,000 --> 00:00:03,000\n私は約束を見る。\n",
        encoding="utf-8",
    )
    analysis = analyze_paths(paths=[subtitle], jlpt_words=load_jlpt_words(jlpt_path))

    glossary = ChineseGlossary({"約束": "约定，约会"})
    payload = analysis_to_dict(analysis, level=4, examples_per_word=2, zh_glossary=glossary)
    output = write_corpus_json(analysis, tmp_path / "corpus.json", level=4, zh_glossary=glossary)

    assert payload["schema_version"] == 6
    assert payload["summary"]["lyric_file_count"] == 0
    assert payload["words"][0]["word"] == "約束"
    assert payload["words"][0]["meaning_zh"] == "约定，约会"
    assert payload["words"][0]["source_type_counts"] == {"subtitle": 1}
    assert payload["words"][0]["examples"][0]["sentence"] == "私は約束を見る。"
    assert payload["words"][0]["examples"][0]["source_type"] == "subtitle"
    assert payload["words"][0]["examples"][0]["matched_text"] == "約束"
    assert payload["words"][0]["examples"][0]["context_before"] == []
    assert payload["words"][0]["examples"][0]["show_context"] == {
        "summary": None,
        "characters": [],
    }
    assert payload["words"][0]["examples"][0]["scene_description"] is None
    assert payload["words"][0]["examples"][0]["translation_zh"] is None
    assert payload["words"][0]["examples"][0]["usage_note_zh"] is None
    assert payload["words"][1]["word"] == "気持ち"
    assert payload["words"][1]["count"] == 0
    assert payload["words"][1]["examples"] == []
    assert output.exists()


def test_example_context_and_reference_format(tmp_path: Path):
    jlpt_path = tmp_path / "jlpt.json"
    write_sample_jlpt(jlpt_path)
    subtitle = tmp_path / "sample.srt"
    subtitle.write_text(
        "1\n00:00:01,000 --> 00:00:03,000\n今日は学校へ行く。\n\n"
        "2\n00:00:04,000 --> 00:00:06,000\n私は約束を見る。\n\n"
        "3\n00:00:07,000 --> 00:00:09,000\n微妙な気持ちだ。\n",
        encoding="utf-8",
    )
    analysis = analyze_paths(
        paths=[subtitle],
        jlpt_words=load_jlpt_words(jlpt_path),
        context_lines=1,
    )

    example = analysis.word_stats["約束"].examples[0]

    assert example.context_before == ["今日は学校へ行く。"]
    assert example.context_after == ["微妙な気持ちだ。"]
    assert format_reference(example) == "《Local subtitles》 sample.srt 00:04"
    assert format_reference(example, brackets=False) == "Local subtitles sample.srt 00:04"
    assert format_timestamp(3_661_000) == "01:01:01"


def test_context_collects_past_short_subtitle_fragments():
    lines = [
        SubtitleLine("これは十分長い前文です。"),
        SubtitleLine("え？"),
        SubtitleLine("現在の字幕です。"),
        SubtitleLine("ん？"),
        SubtitleLine("それから説明が続きます。"),
    ]

    assert collect_context(
        lines,
        line_index=2,
        direction="before",
        preferred_lines=1,
        min_chars=10,
        max_lines=3,
    ) == ["これは十分長い前文です。", "え？"]
    assert collect_context(
        lines,
        line_index=2,
        direction="after",
        preferred_lines=1,
        min_chars=10,
        max_lines=3,
    ) == ["ん？", "それから説明が続きます。"]


def test_analysis_combines_subtitles_and_lyrics(tmp_path: Path):
    jlpt_path = tmp_path / "jlpt.json"
    write_sample_jlpt(jlpt_path)
    subtitle = tmp_path / "sample.srt"
    subtitle.write_text(
        "1\n00:00:01,000 --> 00:00:03,000\n私は約束を見る。\n",
        encoding="utf-8",
    )
    lyric = tmp_path / "song.lrc"
    lyric.write_text(
        "[00:01.00]約束を見ている\n"
        "[00:04.00]微妙な気持ち\n",
        encoding="utf-8",
    )

    analysis = analyze_media(
        watched_show_count=1,
        music_track_count=1,
        subtitle_files=[
            SubtitleFile(
                bangumi_id=1,
                show_title="Sample Show",
                path=subtitle,
                name=subtitle.name,
                episode=1,
            )
        ],
        lyric_files=[
            LyricFile(
                track_key="track-1",
                bangumi_id=2,
                track_title="Sample Song",
                album_title="Sample Album",
                path=lyric,
                provider="lrclib",
                artist="Sample Artist",
                synced=True,
            )
        ],
        jlpt_words=load_jlpt_words(jlpt_path),
        context_lines=1,
    )
    payload = analysis_to_dict(analysis, level=4, examples_per_word=5)

    assert payload["summary"]["subtitle_file_count"] == 1
    assert payload["summary"]["music_track_count"] == 1
    assert payload["summary"]["lyric_file_count"] == 1
    assert payload["words"][0]["word"] == "約束"
    assert payload["words"][0]["source_type_counts"] == {"subtitle": 1, "lyrics": 1}
    assert {example["source_type"] for example in payload["words"][0]["examples"]} == {
        "subtitle",
        "lyrics",
    }
    lyric_example = next(
        example for example in payload["words"][0]["examples"] if example["source_type"] == "lyrics"
    )
    assert lyric_example["source_artist"] == "Sample Artist"
    assert lyric_example["source_album"] == "Sample Album"


def test_clean_subtitle_text_preserves_cue_line_breaks():
    assert clean_subtitle_text("一行目\n  二行目  \n") == "一行目\n二行目"


def test_parse_jlpt_level_from_tags():
    assert parse_level("JLPT_1 JLPT") == 1
    assert parse_level("JLPT_5 JLPT") == 5


def test_study_candidate_filter_removes_function_words():
    assert not is_study_candidate("と", "助詞")
    assert not is_study_candidate("何", "代名詞")
    assert not is_study_candidate("する", "動詞")
    assert is_study_candidate("約束", "名詞")


def test_analysis_skips_katakana_word_embedded_in_longer_katakana_name(tmp_path: Path):
    words = load_jlpt_words_from_entries(
        [WordEntry(surface="ベルト", reading="ベルト", level=2)]
    )
    subtitle = tmp_path / "sample.srt"
    subtitle.write_text(
        "1\n00:00:01,000 --> 00:00:03,000\n君はギルベルトから何を聞いた？\n\n"
        "2\n00:00:04,000 --> 00:00:06,000\nベルトを締める。\n",
        encoding="utf-8",
    )

    analysis = analyze_paths(paths=[subtitle], jlpt_words=words)

    stats = analysis.word_stats["ベルト"]
    assert stats.count == 1
    assert [example.sentence for example in stats.examples] == ["ベルトを締める。"]


def test_to_hiragana():
    assert to_hiragana("ヤクソク") == "やくそく"


def test_jlpt_duplicate_surface_prefers_basic_level_reading():
    words = load_jlpt_words_from_entries(
        [
            WordEntry(surface="来る", reading="きたる", level=1),
            WordEntry(surface="来る", reading="くる", level=5),
        ]
    )

    entry = words.lookup("来る")

    assert entry is not None
    assert entry.level == 5
    assert entry.reading == "くる"


def test_clean_chinese_gloss_removes_leading_reading():
    assert clean_gloss("（みる）①【他动2】看，观看") == "①【他动2】看，观看"
    assert clean_gloss("(いま1) 现在") == "现在"


def test_select_examples_prefers_quality_and_source_diversity():
    examples = [
        WordExample(
            sentence="見る",
            source_title="Show A",
            subtitle_file="a.srt",
            matched_text="見る",
        ),
        WordExample(
            sentence="これは見る価値がある作品です。",
            source_title="Show A",
            subtitle_file="a.srt",
            matched_text="見る",
            context_before=["前の台詞"],
            context_after=["次の台詞"],
        ),
        WordExample(
            sentence="明日また見ることにした。",
            source_title="Show B",
            subtitle_file="b.srt",
            matched_text="見る",
            context_before=["前の台詞"],
            context_after=["次の台詞"],
        ),
    ]

    selected = _select_examples(examples, limit=2)

    assert {example.source_title for example in selected} == {"Show A", "Show B"}
    assert all(example.sentence != "見る" for example in selected)


def test_select_examples_uses_stable_hash_tiebreaker():
    examples = [
        WordExample(
            sentence="今日は見ることにした。",
            source_title="Show A",
            subtitle_file="a.srt",
            matched_text="見る",
        ),
        WordExample(
            sentence="明日も見ることにした。",
            source_title="Show B",
            subtitle_file="b.srt",
            matched_text="見る",
        ),
        WordExample(
            sentence="今夜は見ることにした。",
            source_title="Show C",
            subtitle_file="c.srt",
            matched_text="見る",
        ),
    ]

    selected = _select_examples(examples, limit=1)
    selected_reversed = _select_examples(list(reversed(examples)), limit=1)

    assert [example.sentence for example in selected] == [
        example.sentence for example in selected_reversed
    ]


def test_word_examples_keep_source_diversity_when_candidate_pool_is_full():
    stats = WordStats(entry=WordEntry(surface="見る", reading="みる", level=5))

    stats.add_example(
        WordExample("見る 1", "Show A", "a.srt", "見る"),
        limit=2,
    )
    stats.add_example(
        WordExample("見る 2", "Show A", "a.srt", "見る"),
        limit=2,
    )
    stats.add_example(
        WordExample("見る 3", "Show B", "b.srt", "見る"),
        limit=2,
    )

    assert {example.source_title for example in stats.examples} == {"Show A", "Show B"}


def load_jlpt_words_from_entries(entries):
    from jpcorpus.jlpt import JLPTWords

    return JLPTWords(entries)
