from pathlib import Path

from jpcorpus.analysis import analyze_paths, is_study_candidate, to_hiragana
from jpcorpus.anki_export import export_anki_deck
from jpcorpus.corpus_export import analysis_to_dict, write_corpus_json
from jpcorpus.jlpt import load_jlpt_words, parse_level, write_sample_jlpt
from jpcorpus.models import WordEntry
from jpcorpus.report import build_markdown_report
from jpcorpus.report import format_reference, format_timestamp
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

    payload = analysis_to_dict(analysis, level=4, examples_per_word=2)
    output = write_corpus_json(analysis, tmp_path / "corpus.json", level=4)

    assert payload["schema_version"] == 2
    assert payload["words"][0]["word"] == "約束"
    assert payload["words"][0]["examples"][0]["sentence"] == "私は約束を見る。"
    assert payload["words"][0]["examples"][0]["matched_text"] == "約束"
    assert payload["words"][0]["examples"][0]["context_before"] == []
    assert payload["words"][0]["examples"][0]["scene_description"] is None
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


def test_parse_jlpt_level_from_tags():
    assert parse_level("JLPT_1 JLPT") == 1
    assert parse_level("JLPT_5 JLPT") == 5


def test_study_candidate_filter_removes_function_words():
    assert not is_study_candidate("と", "助詞")
    assert not is_study_candidate("何", "代名詞")
    assert not is_study_candidate("する", "動詞")
    assert is_study_candidate("約束", "名詞")


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


def load_jlpt_words_from_entries(entries):
    from jpcorpus.jlpt import JLPTWords

    return JLPTWords(entries)
