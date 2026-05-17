from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from jpcorpus import user_dictionaries as dictionaries


def write_yomitan_zip(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("index.json", json.dumps({"title": "Test Chinese"}))
        archive.writestr(
            "term_bank_1.json",
            json.dumps(
                [
                    ["行く", "いく", "v5k", "", 10, ["去；到"], 1, "common"],
                    [
                        "ありがとう",
                        "",
                        "exp",
                        "",
                        5,
                        [{"type": "structured-content", "content": "谢谢"}],
                        2,
                        "",
                    ],
                ],
                ensure_ascii=False,
            ),
        )


def test_yomitan_dictionary_import_and_lookup(tmp_path):
    source = tmp_path / "test.zip"
    write_yomitan_zip(source)

    result = dictionaries.import_dictionary_file(source, base_dir=tmp_path / "dicts")
    assert result["imported"] is True
    assert result["dictionary"]["name"] == "Test Chinese"
    assert result["dictionary"]["stats"]["headword_count"] == 2

    matches = dictionaries.lookup_user_dictionaries({"word": "行く", "reading": "いく"}, base_dir=tmp_path / "dicts")
    assert matches[0]["dictionary_name"] == "Test Chinese"
    assert matches[0]["definitions"] == ["去；到"]

    duplicate = dictionaries.import_dictionary_file(source, base_dir=tmp_path / "dicts")
    assert duplicate["imported"] is False


def test_yomitan_dictionary_upload_imports_stream(tmp_path):
    source = tmp_path / "test.zip"
    write_yomitan_zip(source)

    result = dictionaries.import_dictionary_upload(
        filename="test.zip",
        stream=io.BytesIO(source.read_bytes()),
        name="Upload Name",
        base_dir=tmp_path / "dicts",
    )

    assert result["imported"] is True
    assert result["dictionary"]["name"] == "Upload Name"
    assert dictionaries.lookup_user_dictionaries("ありがとう", base_dir=tmp_path / "dicts")[0]["definitions"] == ["谢谢"]


def test_yomitan_structured_content_keeps_primary_glosses_only(tmp_path):
    source = tmp_path / "wty.zip"
    structured = {
        "type": "structured-content",
        "content": [
            {
                "tag": "div",
                "content": [
                    {
                        "tag": "details",
                        "data": {"content": "details-entry-Etymology"},
                        "content": [
                            {"tag": "summary", "content": "词源"},
                            {"tag": "div", "content": "源自古日语。"},
                        ],
                    }
                ],
            },
            {
                "tag": "ol",
                "data": {"content": "glosses"},
                "content": [
                    {
                        "tag": "li",
                        "content": [
                            {
                                "tag": "div",
                                "content": [
                                    "去，前往",
                                    {
                                        "tag": "details",
                                        "data": {"content": "details-entry-examples"},
                                        "content": [{"tag": "summary", "content": "3 例"}, "例句"],
                                    },
                                ],
                            }
                        ],
                    },
                    {"tag": "li", "content": [{"tag": "div", "content": "送达"}]},
                    {"tag": "li", "content": [{"tag": "div", "content": "行く：抵达"}]},
                    {
                        "tag": "li",
                        "content": [
                            {
                                "tag": "div",
                                "content": "行く【いく】\n自五\n1. 离开，逝去。\nゆく年くる年。\n冬去春来。\n2. 进展顺利。",
                            }
                        ],
                    },
                ],
            },
            {
                "tag": "div",
                "data": {"content": "backlink"},
                "content": [{"tag": "a", "content": "Wiktionary"}, " | ", {"tag": "a", "content": "Kaikki"}],
            },
        ],
    }
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("index.json", json.dumps({"title": "WTY"}))
        archive.writestr(
            "term_bank_1.json",
            json.dumps([["行く", "", "v godan vi", "v", 0, [structured]]], ensure_ascii=False),
        )

    dictionaries.import_dictionary_file(source, base_dir=tmp_path / "dicts")

    matches = dictionaries.lookup_user_dictionaries("行く", base_dir=tmp_path / "dicts")
    assert matches[0]["definitions"] == ["去，前往", "送达", "抵达", "离开，逝去", "进展顺利"]


def test_yomitan_reference_entries_are_classified(tmp_path):
    source = tmp_path / "wty.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("index.json", json.dumps({"title": "WTY"}))
        archive.writestr(
            "term_bank_1.json",
            json.dumps(
                [
                    ["見る", "", "non-lemma", "v", 0, [["みる", ["alternative kanji"]]]],
                    ["良い", "", "adj", "adj", 0, ["好的"]],
                    ["良い", "", "non-lemma", "adj", 0, [["善い", ["alt-of"]]]],
                    ["いい", "", "non-lemma", "v", 0, [["いう", ["redirected from いい"]]]],
                ],
                ensure_ascii=False,
            ),
        )

    dictionaries.import_dictionary_file(source, base_dir=tmp_path / "dicts")

    references = dictionaries.lookup_user_dictionaries("見る", base_dir=tmp_path / "dicts")
    assert references[0]["kind"] == "reference"
    assert references[0]["reference_type"] == "spelling"
    assert references[0]["references"] == ["みる"]

    matches = dictionaries.lookup_user_dictionaries("良い", base_dir=tmp_path / "dicts")
    assert matches[0]["definitions"] == ["好的"]
    assert matches[1]["kind"] == "reference"
    assert matches[1]["reference_type"] == "see_also"
    assert matches[1]["references"] == ["善い"]
    assert dictionaries.lookup_user_dictionaries("いい", base_dir=tmp_path / "dicts") == []


def test_dictionary_enable_toggle_controls_lookup(tmp_path):
    source = tmp_path / "test.zip"
    write_yomitan_zip(source)
    result = dictionaries.import_dictionary_file(source, base_dir=tmp_path / "dicts")
    dictionary_id = result["dictionary"]["id"]

    dictionaries.update_dictionary_record(dictionary_id, {"enabled": False}, base_dir=tmp_path / "dicts")

    assert dictionaries.lookup_user_dictionaries("行く", base_dir=tmp_path / "dicts") == []


def test_mdx_dictionary_indexes_keys_and_strips_html(tmp_path, monkeypatch):
    class FakeMDX:
        def __init__(self, fname):
            self._fname = fname
            self._version = 2
            self._key_list = [(0, "大統領".encode("utf-8")), (20, "行く".encode("utf-8"))]

    def fake_read_record(_mdx, *, key, offset, length):
        assert key == "大統領".encode("utf-8")
        assert offset == 0
        assert length == 20
        return "<div>总统<br>国家元首</div>"

    monkeypatch.setattr(dictionaries, "import_mdx_class", lambda: FakeMDX)
    monkeypatch.setattr(dictionaries, "read_mdx_record", fake_read_record)
    source = tmp_path / "test.mdx"
    source.write_bytes(b"fake")

    result = dictionaries.import_dictionary_file(source, name="MDict", base_dir=tmp_path / "dicts")
    assert result["dictionary"]["format"] == "mdx"

    matches = dictionaries.lookup_user_dictionaries("大統領", base_dir=tmp_path / "dicts")
    assert matches[0]["dictionary_name"] == "MDict"
    assert matches[0]["definitions"] == ["总统\n国家元首"]
