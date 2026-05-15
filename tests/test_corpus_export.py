import gzip
import json
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
from jpcorpus.corpus_export import (
    _select_examples,
    analysis_to_dict,
    corpus_index_path,
    corpus_source_details_dir,
    corpus_word_details_dir,
    source_document_key,
    source_detail_path,
    word_detail_path,
    write_corpus_json,
)
from jpcorpus.jlpt import load_jlpt_words, parse_level, write_sample_jlpt
from jpcorpus.lexical_notes import LexicalResourceIndex, label_pos
from jpcorpus.models import LyricFile, SubtitleFile, SubtitleLine, TextFile, WordEntry
from jpcorpus.subtitle import clean_subtitle_text
from jpcorpus.texts import discover_text_files, parse_text, text_file_from_path

from jpcorpus.zh_dict import (
    ChineseGlossary,
    build_zhwiktionary_ja_dict,
    clean_gloss,
    extract_gloss_readings,
)


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
    index_path = corpus_index_path(output)
    assert index_path.exists()
    index_payload = json.loads(index_path.read_text(encoding="utf-8"))
    assert index_payload["words"][0]["word"] == "約束"
    assert "examples" not in index_payload["words"][0]
    assert "lexical_notes" not in index_payload["words"][0]
    assert index_payload["words"][0]["example_count"] == 1
    assert "約束" in index_payload["words"][0]["search_terms"]
    assert index_payload["sources"][0]["source_key"]
    assert index_payload["sources"][0]["line_count"] == 1
    assert index_payload["sources"][0]["words"] == ["約束"]
    assert "lines" not in index_payload["sources"][0]
    assert index_payload["words"][0]["annotation_surfaces"] == ["約束"]
    word_detail = json.loads(word_detail_path(output, "約束").read_text(encoding="utf-8"))
    source_detail = json.loads(
        source_detail_path(output, source_document_key(payload["sources"][0])).read_text(encoding="utf-8")
    )
    assert word_detail["examples"][0]["sentence"] == "私は約束を見る。"
    assert source_detail["lines"][0]["text"] == "私は約束を見る。"
    assert corpus_word_details_dir(output).is_dir()
    assert corpus_source_details_dir(output).is_dir()


def test_analysis_to_dict_can_skip_zero_count_words(tmp_path: Path):
    jlpt_path = tmp_path / "jlpt.json"
    write_sample_jlpt(jlpt_path)
    subtitle = tmp_path / "sample.srt"
    subtitle.write_text(
        "1\n00:00:01,000 --> 00:00:03,000\n私は約束を見る。\n",
        encoding="utf-8",
    )
    analysis = analyze_paths(paths=[subtitle], jlpt_words=load_jlpt_words(jlpt_path))

    payload = analysis_to_dict(analysis, include_zero_count_words=False)

    words = {word["word"]: word for word in payload["words"]}
    assert "気持ち" not in words
    assert words["約束"]["count"] == 1
    assert words["見る"]["count"] == 1


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


def test_chinese_glossary_does_not_use_reading_for_kanji_homophones(tmp_path: Path):
    jlpt_path = tmp_path / "jlpt.json"
    jlpt_path.write_text(
        '[{"word":"音","reading":"おと","level":"N5","meaning":"sound"}]',
        encoding="utf-8",
    )
    analysis = analyze_paths(paths=[], jlpt_words=load_jlpt_words(jlpt_path))

    payload = analysis_to_dict(
        analysis,
        zh_glossary=ChineseGlossary({"おと": "wrong homophone fallback"}),
    )
    word = next(word for word in payload["words"] if word["word"] == "音")

    assert word["meaning_zh"] is None


def test_chinese_glossary_skips_surface_entry_with_mismatched_reading(tmp_path: Path):
    jlpt_path = tmp_path / "jlpt.json"
    jlpt_path.write_text(
        '[{"word":"音","reading":"おと","level":"N5","meaning":"sound"}]',
        encoding="utf-8",
    )
    analysis = analyze_paths(paths=[], jlpt_words=load_jlpt_words(jlpt_path))

    payload = analysis_to_dict(
        analysis,
        zh_glossary=ChineseGlossary({"音": "发音，读音，字音"}, {"音": ("おん",)}),
    )
    word = next(word for word in payload["words"] if word["word"] == "音")

    assert word["meaning_zh"] is None


def test_chinese_glossary_uses_lexical_base_reading_for_inflected_words(tmp_path: Path):
    jlpt_path = tmp_path / "jlpt.json"
    jlpt_path.write_text(
        '[{"word":"付き合う","reading":"つきあう","level":"N3","meaning":"to associate"}]',
        encoding="utf-8",
    )
    subtitle = tmp_path / "sample.srt"
    subtitle.write_text(
        "1\n00:00:01,000 --> 00:00:03,000\n付き合っている。\n",
        encoding="utf-8",
    )
    jmdict = tmp_path / "JMdict.xml"
    jmdict.write_text(
        "<JMdict>"
        "<entry>"
        "<ent_seq>1</ent_seq>"
        "<k_ele><keb>付き合う</keb><ke_pri>news1</ke_pri></k_ele>"
        "<r_ele><reb>つきあう</reb><re_pri>news1</re_pri></r_ele>"
        "<sense><pos>Godan verb with 'u' ending</pos><gloss>to associate with</gloss></sense>"
        "</entry>"
        "</JMdict>",
        encoding="utf-8",
    )
    analysis = analyze_paths(paths=[subtitle], jlpt_words=load_jlpt_words(jlpt_path))

    payload = analysis_to_dict(
        analysis,
        jmdict_path=jmdict,
        zh_glossary=ChineseGlossary({"付き合う": "交往"}, {"付き合う": ("つきあう",)}),
    )
    word = next(word for word in payload["words"] if word["word"] == "付き合う")

    assert word["meaning_zh"] == "交往"


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
    analysis = analyze_paths(paths=[subtitle], jlpt_words=load_jlpt_words(jlpt_path))

    payload = analysis_to_dict(
        analysis,
        level=4,
        examples_per_word=2,
        jmdict_path=jmdict,
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
    assert "kanji" not in notes
    coverage = payload["summary"]["word_source_coverage"]
    assert coverage["exported_dictionary_example_word_count"] >= 1
    assert coverage["exported_no_jmdict_word_count"] >= 0
    assert coverage["exported_missing_zh_meaning_word_count"] >= 0


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
        target_keys={"とき"},
    )
    notes = index.notes_for("とき", "とき")

    assert notes is not None
    assert notes["senses"][0]["glosses"] == ["time"]
    assert index.canonical_surface("とき", "とき") == "時"


def test_jmdict_notes_do_not_use_reading_fallback_for_kanji_homophones(tmp_path: Path):
    jmdict = tmp_path / "JMdict.xml"
    jmdict.write_text(
        "<JMdict>"
        "<entry>"
        "<ent_seq>1</ent_seq>"
        "<k_ele><keb>司会</keb></k_ele>"
        "<r_ele><reb>しかい</reb></r_ele>"
        "<sense><pos>noun (common) (futsuumeishi)</pos><gloss>host</gloss></sense>"
        "</entry>"
        "</JMdict>",
        encoding="utf-8",
    )

    index = LexicalResourceIndex.load_optional(
        jmdict_path=jmdict,
        target_keys={"視界", "しかい"},
    )

    assert index.notes_for("視界", "しかい") is None
    assert not index.has_jmdict_entry("視界", "しかい")
    assert index.notes_for("しかい", "しかい")["senses"][0]["glosses"] == ["host"]


def test_chinese_glossary_can_use_jmdict_spelling_for_kana_words(tmp_path: Path):
    jlpt_path = tmp_path / "jlpt.json"
    jlpt_path.write_text(
        '[{"word":"とき","reading":"とき","level":"N5","meaning":"time"}]',
        encoding="utf-8",
    )
    jmdict = tmp_path / "JMdict.xml"
    jmdict.write_text(
        "<JMdict>"
        "<entry>"
        "<ent_seq>1</ent_seq>"
        "<k_ele><keb>時</keb><ke_pri>news1</ke_pri></k_ele>"
        "<r_ele><reb>とき</reb><re_pri>news1</re_pri></r_ele>"
        "<sense><pos>noun (common) (futsuumeishi)</pos><gloss>time</gloss></sense>"
        "</entry>"
        "</JMdict>",
        encoding="utf-8",
    )
    analysis = analyze_paths(paths=[], jlpt_words=load_jlpt_words(jlpt_path))

    payload = analysis_to_dict(
        analysis,
        jmdict_path=jmdict,
        zh_glossary=ChineseGlossary({"時": "时候"}),
    )
    word = next(word for word in payload["words"] if word["word"] == "とき")

    assert word["meaning_zh"] == "时候"


def test_jmdict_pos_labels_cover_verbose_english_tags():
    assert label_pos("noun or participle which takes the aux. verb suru") == "する名词"
    assert label_pos("nouns which may take the genitive case particle 'no'") == "の名词"
    assert label_pos("adverb taking the 'to' particle") == "と副词"
    assert label_pos("suru verb - special class") == "サ变"


def test_example_context_from_neighboring_subtitles(tmp_path: Path):
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


def test_text_file_uses_sidecar_metadata_title(tmp_path: Path):
    text = tmp_path / "web" / "imported.txt"
    text.parent.mkdir()
    text.write_text("今日は学校へ行く。", encoding="utf-8")
    text.with_name("imported.meta.json").write_text(
        '{"title": "ウェブ記事", "author": "Sample Author"}',
        encoding="utf-8",
    )

    text_file = text_file_from_path(text, root=tmp_path)

    assert text_file.title == "ウェブ記事"
    assert text_file.author == "Sample Author"
    assert text_file.name == "web/imported.txt"


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
    assert clean_gloss("（いい/よい）①【イ形】好的") == "①【イ形】好的"


def test_chinese_gloss_reading_prefixes_are_used_for_matching(tmp_path: Path):
    path = tmp_path / "dict.json"
    path.write_text('{"雨": "（あめ）名词 雨"}', encoding="utf-8")

    glossary = ChineseGlossary.load(path)

    assert extract_gloss_readings("（いい/よい）①【イ形】好的") == ("いい", "よい")
    assert glossary.lookup("雨", reading="あめ") == "名词 雨"
    assert glossary.lookup("雨", reading="あま") is None


def test_chinese_glossary_matches_multi_reading_words(tmp_path: Path):
    path = tmp_path / "dict.json"
    path.write_text('{"良い": "（いい/よい）①【イ形】好的"}', encoding="utf-8")

    glossary = ChineseGlossary.load(path)

    assert glossary.lookup("良い", reading="よい; いい") == "①【イ形】好的"


def test_zhwiktionary_japanese_glossary_is_loaded_as_primary_source(tmp_path: Path):
    raw_path = tmp_path / "zhwiktionary.jsonl.gz"
    output = tmp_path / "zhwiktionary-ja.json"
    fallback = tmp_path / "fallback.json"
    rows = [
        {
            "word": "アイス",
            "lang_code": "ja",
            "pos": "noun",
            "pos_title": "名詞",
            "forms": [{"form": "aisu", "tags": ["romanization"]}],
            "senses": [{"glosses": ["冰"]}, {"glosses": ["冰棒", "冰淇淋"]}],
        },
        {
            "word": "字",
            "lang_code": "ja",
            "pos": "character",
            "pos_title": "漢字",
            "senses": [{"glosses": ["character entry should not become a word gloss"]}],
        },
        {
            "word": "鳴き声",
            "lang_code": "ja",
            "pos": "noun",
            "pos_title": "名詞",
            "senses": [{"glosses": ["動物的叫聲"]}],
        },
        {
            "word": "聞く",
            "lang_code": "ja",
            "pos": "verb",
            "pos_title": "動詞",
            "senses": [
                {"glosses": ["聞く，聴く： 聆聽，欣賞"]},
                {"glosses": ["聞く，訊く： 打聽，詢問"]},
                {"glosses": ["聞く： 答應，聽從"]},
                {"glosses": ["聞く： 嗅，聞"]},
            ],
        },
    ]
    with gzip.open(raw_path, "wt", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    fallback.write_text('{"アイス": "fallback"}', encoding="utf-8")

    build_zhwiktionary_ja_dict(raw_path, output)
    fallback_glossary = ChineseGlossary.load(fallback)
    wiktionary_glossary = ChineseGlossary.load(output)
    glossary = ChineseGlossary(
        {**fallback_glossary.entries, **wiktionary_glossary.entries},
        {**fallback_glossary.readings, **wiktionary_glossary.readings},
        {**fallback_glossary.parts_of_speech, **wiktionary_glossary.parts_of_speech},
    )

    assert glossary.lookup("アイス") == "冰；冰棒，冰淇淋"
    assert glossary.lookup_parts_of_speech("アイス") == ("名词",)
    assert glossary.lookup("鳴き声") == "动物的叫声"
    assert glossary.lookup_parts_of_speech("鳴き声") == ("名词",)
    assert glossary.lookup("聞く") == "聆听，欣赏；打听，询问；答应，听从；嗅，闻"
    assert glossary.lookup("字") is None


def test_zhwiktionary_pos_fills_lexical_notes_when_jmdict_is_missing(tmp_path: Path):
    jlpt_path = tmp_path / "jlpt.json"
    jlpt_path.write_text(
        '[{"word":"アイス","reading":"あいす","level":"N5","meaning":"ice"}]',
        encoding="utf-8",
    )
    analysis = analyze_paths(paths=[], jlpt_words=load_jlpt_words(jlpt_path))
    glossary = ChineseGlossary(
        {"アイス": "冰"},
        {"アイス": ("あいす",)},
        {"アイス": ("名词",)},
    )

    payload = analysis_to_dict(analysis, zh_glossary=glossary, jmdict_path=None)
    word = next(word for word in payload["words"] if word["word"] == "アイス")

    assert word["meaning_zh"] == "冰"
    assert word["lexical_notes"]["parts_of_speech"] == ["名词"]
    assert "senses" not in word["lexical_notes"]


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
