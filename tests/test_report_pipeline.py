from pathlib import Path

from jpcorpus.analysis import analyze_paths
from jpcorpus.anki_export import export_anki_deck
from jpcorpus.jlpt import load_jlpt_words, write_sample_jlpt
from jpcorpus.report import build_markdown_report


def test_report_from_local_srt(tmp_path: Path):
    jlpt_path = tmp_path / "jlpt.json"
    write_sample_jlpt(jlpt_path)
    subtitle = tmp_path / "sample.srt"
    subtitle.write_text(
        "1\n00:00:01,000 --> 00:00:03,000\n私は約束を見る。\n\n"
        "2\n00:00:04,000 --> 00:00:06,000\n微妙な気持ちだ。\n",
        encoding="utf-8",
    )

    analysis = analyze_paths(paths=[subtitle], jlpt_words=load_jlpt_words(jlpt_path))
    report = build_markdown_report(analysis, target_level=3, top=10)
    english_report = build_markdown_report(analysis, target_level=3, top=10, language="en")

    assert "你的日语个人词频报告" in report
    assert "Your Personal Japanese Frequency Report" in english_report
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
