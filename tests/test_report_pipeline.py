import zipfile
from pathlib import Path

from jpcorpus.analysis import (
    WordExample,
    WordStats,
    analyze_media,
    analyze_paths,
    build_character_aliases,
    collect_context,
    is_study_candidate,
    to_hiragana,
)
from jpcorpus.anki_export import export_anki_deck
from jpcorpus.corpus_export import _select_examples, analysis_to_dict, write_corpus_json
from jpcorpus.jlpt import load_jlpt_words, parse_level, write_sample_jlpt
from jpcorpus.lexical_notes import LexicalResourceIndex, label_pos
from jpcorpus.models import LyricFile, SubtitleFile, SubtitleLine, TextFile, WordEntry
from jpcorpus.report import build_markdown_report
from jpcorpus.report import format_reference, format_timestamp
from jpcorpus.subtitle import clean_subtitle_text
from jpcorpus.texts import discover_text_files, parse_text, text_file_from_path
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

    assert payload["schema_version"] == 13
    assert payload["summary"]["lyric_file_count"] == 0
    assert payload["sources"][0]["source_type"] == "subtitle"
    assert payload["sources"][0]["source_file"] == "sample.srt"
    assert payload["sources"][0]["lines"][0]["text"] == "私は約束を見る。"
    assert payload["sources"][0]["lines"][0]["matches"][0]["word"] == "約束"
    assert payload["sources"][0]["lines"][0]["matches"][0]["matched_text"] == "約束"
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


def test_kanji_tokens_do_not_fall_back_to_homophone_jlpt_entry(tmp_path: Path):
    jlpt_path = tmp_path / "jlpt.json"
    jlpt_path.write_text(
        '[{"word":"司会","reading":"しかい","level":"N2","meaning":"host"}]',
        encoding="utf-8",
    )
    subtitle = tmp_path / "sample.srt"
    subtitle.write_text(
        "1\n00:00:01,000 --> 00:00:03,000\n視界が赤い。\n",
        encoding="utf-8",
    )

    analysis = analyze_paths(paths=[subtitle], jlpt_words=load_jlpt_words(jlpt_path))
    matches = analysis.source_documents[0].lines[0].matches

    assert any(match.word == "視界" and match.matched_text == "視界" for match in matches)
    assert all(match.word != "司会" for match in matches)


def test_export_corpus_json_can_include_jmdict_matched_corpus_words(tmp_path: Path):
    jlpt_path = tmp_path / "jlpt.json"
    write_sample_jlpt(jlpt_path)
    subtitle = tmp_path / "sample.srt"
    subtitle.write_text(
        "1\n00:00:01,000 --> 00:00:03,000\n猫を見る。\n",
        encoding="utf-8",
    )
    jmdict = tmp_path / "JMdict.xml"
    jmdict.write_text(
        "<JMdict>"
        "<entry>"
        "<ent_seq>1</ent_seq>"
        "<k_ele><keb>猫</keb><ke_pri>news1</ke_pri></k_ele>"
        "<r_ele><reb>ねこ</reb><re_pri>news1</re_pri></r_ele>"
        "<sense><pos>noun (common) (futsuumeishi)</pos><gloss>cat</gloss></sense>"
        "</entry>"
        "</JMdict>",
        encoding="utf-8",
    )
    analysis = analyze_paths(paths=[subtitle], jlpt_words=load_jlpt_words(jlpt_path))

    payload = analysis_to_dict(analysis, examples_per_word=2, jmdict_path=jmdict)
    cat = next(word for word in payload["words"] if word["word"] == "猫")

    assert cat["level"] is None
    assert cat["level_number"] is None
    assert cat["reading"] == "ねこ"
    assert cat["meaning"] == "cat"
    assert cat["count"] == 1
    assert cat["lexical_notes"]["senses"][0]["glosses"] == ["cat"]
    assert payload["summary"]["word_source_coverage"]["corpus_jmdict_match_count"] >= 1


def test_level_export_does_not_include_ungraded_corpus_words(tmp_path: Path):
    jlpt_path = tmp_path / "jlpt.json"
    write_sample_jlpt(jlpt_path)
    subtitle = tmp_path / "sample.srt"
    subtitle.write_text(
        "1\n00:00:01,000 --> 00:00:03,000\n猫を見る。\n",
        encoding="utf-8",
    )
    jmdict = tmp_path / "JMdict.xml"
    jmdict.write_text(
        "<JMdict>"
        "<entry>"
        "<ent_seq>1</ent_seq>"
        "<k_ele><keb>猫</keb></k_ele>"
        "<r_ele><reb>ねこ</reb></r_ele>"
        "<sense><gloss>cat</gloss></sense>"
        "</entry>"
        "</JMdict>",
        encoding="utf-8",
    )
    analysis = analyze_paths(paths=[subtitle], jlpt_words=load_jlpt_words(jlpt_path))

    payload = analysis_to_dict(analysis, level=5, examples_per_word=2, jmdict_path=jmdict)

    assert "猫" not in {word["word"] for word in payload["words"]}
    assert "見る" in {word["word"] for word in payload["words"]}


def test_export_corpus_json_includes_offline_lexical_notes(tmp_path: Path):
    jlpt_path = tmp_path / "jlpt.json"
    write_sample_jlpt(jlpt_path)
    subtitle = tmp_path / "sample.srt"
    subtitle.write_text(
        "1\n00:00:01,000 --> 00:00:03,000\n私は約束を見る。\n",
        encoding="utf-8",
    )
    jmdict = tmp_path / "JMdict.xml"
    jmdict.write_text(
        "<JMdict>"
        "<entry>"
        "<ent_seq>1</ent_seq>"
        "<k_ele><keb>約束</keb><ke_pri>news1</ke_pri></k_ele>"
        "<k_ele><keb>約束け</keb><ke_inf>rarely used kanji form</ke_inf></k_ele>"
        "<r_ele><reb>やくそく</reb><re_pri>news1</re_pri></r_ele>"
        "<sense>"
        "<pos>noun (common) (futsuumeishi)</pos>"
        "<misc>word usually written using kana alone</misc>"
        "<s_inf>English sense notes should not appear in the compact UI.</s_inf>"
        "<gloss>promise</gloss>"
        "<example>"
        '<ex_srce exsrc_type="tat">162365</ex_srce>'
        "<ex_text>約束</ex_text>"
        '<ex_sent xml:lang="jpn">その約束を覚えている。</ex_sent>'
        '<ex_sent xml:lang="eng">I remember that promise.</ex_sent>'
        "</example>"
        "</sense>"
        "</entry>"
        "</JMdict>",
        encoding="utf-8",
    )
    kanjidic2 = tmp_path / "kanjidic2.xml"
    kanjidic2.write_text(
        "<kanjidic2>"
        "<character>"
        "<literal>約</literal>"
        "<misc><grade>4</grade><jlpt>3</jlpt></misc>"
        "<reading_meaning><rmgroup>"
        '<reading r_type="ja_on">ヤク</reading>'
        '<reading r_type="ja_kun">つづ.まる</reading>'
        "<meaning>promise</meaning>"
        "</rmgroup></reading_meaning>"
        "</character>"
        "</kanjidic2>",
        encoding="utf-8",
    )
    analysis = analyze_paths(paths=[subtitle], jlpt_words=load_jlpt_words(jlpt_path))

    payload = analysis_to_dict(
        analysis,
        level=4,
        examples_per_word=2,
        jmdict_path=jmdict,
        kanjidic2_path=kanjidic2,
    )
    notes = payload["words"][0]["lexical_notes"]

    assert notes["spellings"][0]["text"] == "約束"
    assert notes["spellings"][0]["common"] is True
    assert [form["text"] for form in notes["spellings"]] == ["約束"]
    assert notes["readings"][0]["text"] == "やくそく"
    assert notes["parts_of_speech"] == ["名词"]
    assert "usage_tags" not in notes
    assert notes["senses"][0]["glosses"] == ["promise"]
    assert notes["senses"][0]["parts_of_speech"] == ["名词"]
    assert notes["dictionary_examples"][0]["japanese"] == "その約束を覚えている。"
    assert notes["dictionary_examples"][0]["translations"] == {
        "eng": "I remember that promise."
    }
    assert notes["dictionary_examples"][0]["source"] == {"id": "162365", "type": "tat"}
    assert notes["kanji"][0]["literal"] == "約"
    assert notes["kanji"][0]["on_readings"] == ["ヤク"]
    assert notes["kanji"][0]["meanings"] == ["promise"]


def test_jmdict_notes_prefer_common_entry_over_exact_kana_suffix(tmp_path: Path):
    jmdict = tmp_path / "JMdict.xml"
    jmdict.write_text(
        "<JMdict>"
        "<entry>"
        "<ent_seq>1</ent_seq>"
        "<r_ele><reb>とき</reb></r_ele>"
        "<sense><pos>suffix</pos><gloss>please do</gloss></sense>"
        "</entry>"
        "<entry>"
        "<ent_seq>2</ent_seq>"
        "<k_ele><keb>時</keb><ke_pri>news1</ke_pri></k_ele>"
        "<r_ele><reb>とき</reb><re_pri>news1</re_pri></r_ele>"
        "<sense><pos>noun (common) (futsuumeishi)</pos><gloss>time</gloss></sense>"
        "</entry>"
        "</JMdict>",
        encoding="utf-8",
    )

    index = LexicalResourceIndex.load_optional(
        jmdict_path=jmdict,
        kanjidic2_path=None,
        target_keys={"とき"},
    )
    notes = index.notes_for("とき", "とき")

    assert notes is not None
    assert notes["senses"][0]["glosses"] == ["time"]
    assert index.canonical_surface("とき", "とき") == "時"


def test_jmdict_pos_labels_cover_verbose_english_tags():
    assert label_pos("noun or participle which takes the aux. verb suru") == "する名词"
    assert label_pos("nouns which may take the genitive case particle 'no'") == "の名词"
    assert label_pos("adverb taking the 'to' particle") == "と副词"
    assert label_pos("suru verb - special class") == "サ变"


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


def test_analysis_includes_local_text_files(tmp_path: Path):
    jlpt_path = tmp_path / "jlpt.json"
    write_sample_jlpt(jlpt_path)
    novel = tmp_path / "sample novel.txt"
    novel.write_text(
        "今日は学校へ行く。\n\n私は約束を見る。明日も行く。\n",
        encoding="utf-8",
    )

    analysis = analyze_media(
        watched_show_count=0,
        music_track_count=0,
        subtitle_files=[],
        lyric_files=[],
        text_files=[
            TextFile(
                title="Sample Novel",
                path=novel,
                name=novel.name,
            )
        ],
        jlpt_words=load_jlpt_words(jlpt_path),
        context_lines=1,
    )
    payload = analysis_to_dict(analysis, level=4, examples_per_word=3)

    assert payload["summary"]["text_file_count"] == 1
    assert payload["words"][0]["word"] == "約束"
    assert payload["words"][0]["source_type_counts"] == {"text": 1}
    assert payload["words"][0]["text_count"] == 1
    assert payload["words"][0]["examples"][0]["source_type"] == "text"
    assert payload["words"][0]["examples"][0]["source_title"] == "Sample Novel"
    assert payload["words"][0]["examples"][0]["subtitle_file"] == "sample novel.txt"
    assert payload["words"][0]["examples"][0]["context_before"] == ["今日は学校へ行く。"]
    assert payload["words"][0]["examples"][0]["context_after"] == ["明日も行く。"]


def test_parse_text_splits_japanese_sentences(tmp_path: Path):
    text = tmp_path / "book.txt"
    text.write_text("第一文です。第二文です！\n\n改行しても同じ段落\nなら一文です。", encoding="utf-8")

    assert [line.text for line in parse_text(text)] == [
        "第一文です。",
        "第二文です！",
        "改行しても同じ段落なら一文です。",
    ]


def test_parse_text_reads_epub_spine_in_order(tmp_path: Path):
    epub = tmp_path / "sample.epub"
    write_sample_epub(epub)

    assert [line.text for line in parse_text(epub)] == [
        "今日は学校へ行く。",
        "私は約束を見る。",
        "明日も行く！",
    ]


def test_epub_text_file_uses_metadata_title_and_creator(tmp_path: Path):
    epub = tmp_path / "fallback title.epub"
    write_sample_epub(epub)

    text_file = text_file_from_path(epub)

    assert text_file.title == "花束 みたいな恋をした"
    assert text_file.author == "坂元 裕二"
    assert text_file.name == "fallback title.epub"


def test_text_file_title_and_name_are_nfc_normalized(tmp_path: Path):
    text = tmp_path / "ノベライズ.txt"
    text.write_text("今日は学校へ行く。", encoding="utf-8")

    text_file = text_file_from_path(text)

    assert text_file.title == "ノベライズ"
    assert text_file.name == "ノベライズ.txt"


def test_discover_text_files_includes_txt_and_epub(tmp_path: Path):
    (tmp_path / "book.txt").write_text("今日は学校へ行く。", encoding="utf-8")
    write_sample_epub(tmp_path / "novel.epub")

    assert [item.name for item in discover_text_files(tmp_path)] == ["book.txt", "novel.epub"]


def test_clean_subtitle_text_preserves_cue_line_breaks():
    assert clean_subtitle_text("一行目\n  二行目  \n") == "一行目\n二行目"


def test_parse_jlpt_level_from_tags():
    assert parse_level("JLPT_1 JLPT") == 1
    assert parse_level("JLPT_5 JLPT") == 5


def test_study_candidate_filter_removes_function_words():
    assert not is_study_candidate("と", "助詞")
    assert not is_study_candidate("何", "代名詞")
    assert not is_study_candidate("する", "動詞")
    assert not is_study_candidate("朋", "名詞", "名詞-固有名詞-人名-名")
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


def test_analysis_skips_bangumi_character_name_aliases(tmp_path: Path):
    words = load_jlpt_words_from_entries(
        [WordEntry(surface="武士", reading="ぶし", level=2, meaning="samurai")]
    )
    subtitle = tmp_path / "sample.srt"
    subtitle.write_text(
        "1\n00:00:01,000 --> 00:00:03,000\n（武士）何だよ あの演奏\n\n"
        "2\n00:00:04,000 --> 00:00:06,000\n（武士(たけし)）頼むよ 冗談だろ？\n\n"
        "3\n00:00:07,000 --> 00:00:09,000\nあれ？ 相座… ブ… ブシ…\n",
        encoding="utf-8",
    )

    analysis = analyze_media(
        watched_show_count=1,
        music_track_count=0,
        subtitle_files=[
            SubtitleFile(
                bangumi_id=1,
                show_title="四月是你的谎言",
                path=subtitle,
                name=subtitle.name,
                show_characters=["相座武士"],
            )
        ],
        lyric_files=[],
        jlpt_words=words,
    )

    assert "武士" not in analysis.word_stats


def test_build_character_aliases_includes_given_name_suffix():
    from jpcorpus.tokenize import JapaneseTokenizer

    aliases = build_character_aliases(["相座武士", "宮園かをり"], JapaneseTokenizer())

    assert "武士" in aliases
    assert "かをり" in aliases


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


def test_jlpt_lookup_can_use_safe_reading_index(tmp_path: Path):
    path = tmp_path / "jlpt.json"
    path.write_text(
        '[{"word":"言う","reading":"いう","level":"N5","meaning":"to say"}]',
        encoding="utf-8",
    )

    words = load_jlpt_words(path)

    assert words.lookup_reading("いう").surface == "言う"


def test_jlpt_common_greeting_overrides_are_beginner_level(tmp_path: Path):
    path = tmp_path / "jlpt.json"
    path.write_text(
        '[{"word":"おはよう","reading":"おはよう","level":"N2","meaning":"Good morning"}]',
        encoding="utf-8",
    )

    entry = load_jlpt_words(path).lookup("おはよう")

    assert entry is not None
    assert entry.level == 5
    assert entry.meaning == "good morning"


def test_clean_chinese_gloss_removes_leading_reading():
    assert clean_gloss("（みる）①【他动2】看，观看") == "①【他动2】看，观看"
    assert clean_gloss("(いま1) 现在") == "现在"


def test_chinese_glossary_has_common_greeting_overrides(tmp_path: Path):
    path = tmp_path / "dict.json"
    path.write_text("{}", encoding="utf-8")

    glossary = ChineseGlossary.load(path)

    assert glossary.lookup("おはよう") == "早上好"
    assert glossary.lookup("ありがとう") == "谢谢"


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


def test_select_examples_deduplicates_whitespace_variant_lyrics():
    examples = [
        WordExample(
            sentence="本当は とても とても 嬉しかったよ",
            source_title="secret base ~君がくれたもの~ (Memento mori Ver.)",
            subtitle_file="memento.lrc",
            matched_text="本当",
            source_type="lyrics",
        ),
        WordExample(
            sentence="本当は とても とても嬉しかったよ",
            source_title="secret base ~君がくれたもの~ (10 years after Ver.)",
            subtitle_file="10years.lrc",
            matched_text="本当",
            source_type="lyrics",
        ),
        WordExample(
            sentence="明日また本当の話をする。",
            source_title="Show B",
            subtitle_file="b.srt",
            matched_text="本当",
            source_type="subtitle",
        ),
    ]

    selected = _select_examples(examples, limit=3)

    assert len(selected) == 2
    assert len([example for example in selected if "secret base" in example.source_title]) == 1


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


def write_sample_epub(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip")
        archive.writestr(
            "META-INF/container.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
""",
        )
        archive.writestr(
            "OEBPS/content.opf",
            """<?xml version="1.0" encoding="UTF-8"?>
<package version="3.0" xmlns="http://www.idpf.org/2007/opf">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>花束　みたいな恋をした</dc:title>
    <dc:creator>坂元 裕二</dc:creator>
  </metadata>
  <manifest>
    <item id="chapter-1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
    <item id="chapter-2" href="chapter2.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chapter-1"/>
    <itemref idref="chapter-2"/>
  </spine>
</package>
""",
        )
        archive.writestr(
            "OEBPS/chapter1.xhtml",
            """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head><title>Skip this title</title></head>
  <body>
    <p>今日は学校へ行く。</p>
    <p>私は<ruby>約束<rt>やくそく</rt></ruby>を見る。</p>
  </body>
</html>
""",
        )
        archive.writestr(
            "OEBPS/chapter2.xhtml",
            """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <body><p>明日も行く！</p></body>
</html>
""",
        )
