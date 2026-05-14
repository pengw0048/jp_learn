import json

import pytest

from jpcorpus.viewer_jobs import (
    ViewerJob,
    ViewerJobRunner,
    composite_maintenance_steps,
    explain_reader_usage,
    import_text_document,
    load_viewer_source_details,
    llm_config_status,
    normalize_maintenance_spec,
    save_viewer_config,
    viewer_config_status,
)
from jpcorpus.corpus_export import source_document_key


def test_normalize_maintenance_spec_accepts_fetch_lyrics_options():
    spec = normalize_maintenance_spec(
        {
            "type": "fetch_lyrics",
            "limit": "12",
            "concurrency": "8",
            "overwrite": True,
        }
    )

    assert spec == {
        "type": "fetch_lyrics",
        "limit": 12,
        "concurrency": 8,
        "overwrite": True,
    }


def test_normalize_maintenance_spec_rejects_unknown_task():
    with pytest.raises(ValueError, match="Unsupported maintenance task"):
        normalize_maintenance_spec({"type": "shell"})


def test_normalize_maintenance_spec_accepts_simple_sync_action():
    spec = normalize_maintenance_spec({"type": "sync_media"})

    assert spec["type"] == "sync_media"
    assert spec["limit"] is None
    assert spec["concurrency"] == 4


def test_maintenance_task_fetch_lyrics_calls_internal_function(monkeypatch, tmp_path):
    calls = {}

    def fake_fetch_lyrics(**kwargs):
        calls.update(kwargs)
        print("Fetched lyrics")

    monkeypatch.setattr("jpcorpus.tasks.fetch_lyrics", fake_fetch_lyrics)
    runner = ViewerJobRunner(corpus_path=tmp_path / "corpus.json", state_db=tmp_path / "state.db")
    job = ViewerJob(id="job", kind="fetch_lyrics")
    spec = normalize_maintenance_spec(
        {
            "type": "fetch_lyrics",
            "limit": 5,
            "concurrency": 3,
            "overwrite": True,
        }
    )

    assert runner._run_maintenance_task(job, spec) == {"ok": True}
    assert calls["state_db"] == tmp_path / "state.db"
    assert calls["limit"] == 5
    assert calls["concurrency"] == 3
    assert calls["overwrite"] is True
    assert calls["force"] is False
    assert any("Fetched lyrics" in line for line in job.log)


def test_maintenance_task_sync_anime_does_not_apply_limit(monkeypatch, tmp_path):
    calls = {}

    def fake_sync(**kwargs):
        calls.update(kwargs)

    monkeypatch.setattr("jpcorpus.tasks.sync", fake_sync)
    runner = ViewerJobRunner(corpus_path=tmp_path / "corpus.json", state_db=tmp_path / "state.db")
    job = ViewerJob(id="job", kind="sync_anime")
    spec = normalize_maintenance_spec({"type": "sync_anime", "limit": 3})

    assert runner._run_maintenance_task(job, spec) == {"ok": True}
    assert calls["state_db"] == tmp_path / "state.db"
    assert calls["max_shows"] is None


def test_maintenance_task_can_fetch_lexical_resources(monkeypatch, tmp_path):
    calls = {}

    def fake_fetch_lexical_resources(**kwargs):
        calls.update(kwargs)

    monkeypatch.setattr("jpcorpus.tasks.fetch_lexical_resources", fake_fetch_lexical_resources)
    runner = ViewerJobRunner(corpus_path=tmp_path / "corpus.json", state_db=tmp_path / "state.db")
    job = ViewerJob(id="job", kind="fetch_lexical_resources")
    spec = normalize_maintenance_spec({"type": "fetch_lexical_resources"})

    assert runner._run_maintenance_task(job, spec) == {"ok": True}
    assert calls["jmdict_output"].name == "JMdict_e.gz"
    assert calls["kanjidic2_output"].name == "kanjidic2.xml.gz"


def test_composite_sync_media_finishes_with_corpus_export():
    spec = normalize_maintenance_spec({"type": "sync_media", "concurrency": 6})

    steps = composite_maintenance_steps(spec)

    assert [step[1]["type"] for step in steps] == [
        "sync_anime",
        "sync_music",
        "fetch_lyrics",
        "export_corpus",
    ]
    assert steps[2][1]["concurrency"] == 6


def test_composite_refresh_all_updates_indexes_before_syncing():
    spec = normalize_maintenance_spec({"type": "refresh_all"})

    steps = composite_maintenance_steps(spec)

    assert [step[1]["type"] for step in steps[:4]] == [
        "fetch_anime_db",
        "fetch_zh_dict",
        "fetch_jlpt_words",
        "fetch_lexical_resources",
    ]
    assert steps[-1][1]["type"] == "export_corpus"


def test_load_viewer_source_details_returns_full_lines(tmp_path):
    source = {
        "source_type": "subtitle",
        "source_title": "Local subtitles",
        "source_artist": "",
        "source_album": "",
        "source_file": "sample.srt",
        "episode": 1,
        "token_count": 3,
        "lines": [
            {
                "text": "私は約束を見る。",
                "start_ms": 1000,
                "end_ms": 3000,
                "matches": [{"word": "約束", "matched_text": "約束"}],
            }
        ],
    }
    corpus = tmp_path / "corpus.json"
    corpus.write_text(json.dumps({"sources": [source]}, ensure_ascii=False), encoding="utf-8")

    payload = load_viewer_source_details(corpus, [source_document_key(source)])

    assert payload["missing"] == []
    assert payload["sources"][0]["source_key"] == source_document_key(source)
    assert payload["sources"][0]["lines"][0]["text"] == "私は約束を見る。"


def test_explain_reader_usage_calls_llm_directly(monkeypatch):
    calls = {}

    class FakeClient:
        def annotate_example(self, word, example):
            calls["word"] = word
            calls["example"] = example
            return {
                "translation_zh": "他要去。",
                "usage_note_zh": "这里的「行く」表示移动到某处。",
                "scene_description": "",
            }

        def close(self):
            calls["closed"] = True

    def fake_client(**kwargs):
        calls["client_kwargs"] = kwargs
        return FakeClient()

    monkeypatch.setattr("jpcorpus.viewer_jobs.resolve_llm_client", fake_client)

    result = explain_reader_usage(
        {
            "provider": "apple",
            "word": {
                "word": "行く",
                "reading": "いく",
                "level": "N5",
                "meaning_zh": "去",
                "meaning": "to go",
            },
            "example": {
                "source_type": "text",
                "source_title": "Book",
                "matched_text": "行く",
                "sentence": "学校へ行く。",
                "context_before": ["朝だ。"],
                "context_after": ["急いだ。"],
            },
        }
    )

    assert calls["client_kwargs"]["provider"] == "apple"
    assert calls["client_kwargs"]["use_show_context"] is False
    assert calls["word"]["word"] == "行く"
    assert calls["example"]["sentence"] == "学校へ行く。"
    assert calls["closed"] is True
    assert result["explanation"]["usage_note_zh"] == "这里的「行く」表示移动到某处。"


def test_explain_reader_usage_answers_reader_question(monkeypatch):
    calls = {}

    class FakeClient:
        def answer_question(self, word, example, question):
            calls["word"] = word
            calls["example"] = example
            calls["question"] = question
            return "这里的「行く」表示移动到学校。"

        def close(self):
            calls["closed"] = True

    def fake_client(**kwargs):
        calls["client_kwargs"] = kwargs
        return FakeClient()

    monkeypatch.setattr("jpcorpus.viewer_jobs.resolve_llm_client", fake_client)

    result = explain_reader_usage(
        {
            "provider": "apple",
            "word": {
                "word": "行く",
                "reading": "いく",
                "level": "N5",
                "meaning_zh": "去",
                "meaning": "to go",
            },
            "example": {
                "source_type": "text",
                "source_title": "Book",
                "matched_text": "行く",
                "sentence": "学校へ行く。",
                "context_before": ["朝だ。"],
                "context_after": ["急いだ。"],
            },
            "question": "这里为什么用行く？",
        }
    )

    assert calls["client_kwargs"]["provider"] == "apple"
    assert calls["word"]["word"] == "行く"
    assert calls["example"]["sentence"] == "学校へ行く。"
    assert calls["question"] == "这里为什么用行く？"
    assert calls["closed"] is True
    assert result == {"answer": "这里的「行く」表示移动到学校。"}


def test_import_text_document_writes_txt_and_metadata(tmp_path):
    result = import_text_document(
        {
            "title": "テスト 記事",
            "url": "https://example.com/article",
            "text": " 一行目です。 \n\n\n 二行目です。 ",
        },
        directory=tmp_path / "texts" / "web",
    )

    text_path = tmp_path / result["path"]
    metadata_path = tmp_path / result["metadata_path"]

    assert text_path.name.endswith("-テスト-記事.txt")
    assert text_path.read_text(encoding="utf-8") == "一行目です。\n\n二行目です。\n"
    assert '"title": "テスト 記事"' in metadata_path.read_text(encoding="utf-8")
    assert result["characters"] == len("一行目です。\n\n二行目です。")


def test_viewer_config_status_reports_missing_keys(monkeypatch):
    for key in (
        "JPCORPUS_BANGUMI_CLIENT_ID",
        "JPCORPUS_BANGUMI_CLIENT_SECRET",
        "JIMAKU_API_KEY",
        "JPCORPUS_LLM_MODEL",
        "JPCORPUS_LLM_API_KEY",
        "OPENAI_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("JPCORPUS_LLM_PROVIDER", "openai-compatible")

    status = viewer_config_status()

    assert status["services"][0]["missing"] == [
        "JPCORPUS_BANGUMI_CLIENT_ID",
        "JPCORPUS_BANGUMI_CLIENT_SECRET",
    ]
    assert status["services"][1]["missing"] == ["JIMAKU_API_KEY"]
    assert status["services"][2]["missing"] == ["JPCORPUS_LLM_MODEL", "JPCORPUS_LLM_API_KEY"]


def test_save_viewer_config_updates_dotenv(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text("JIMAKU_API_KEY=old\nUNCHANGED=yes\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("JIMAKU_API_KEY", "old")

    config = save_viewer_config(
        {
            "jimaku_api_key": "new",
            "llm_provider": "openai-compatible",
            "llm_model": "Qwen/Qwen2.5-7B-Instruct",
            "llm_base_url": "https://api.siliconflow.cn/v1",
            "llm_api_key": "sk-test",
        }
    )

    text = env_path.read_text(encoding="utf-8")
    assert "JIMAKU_API_KEY=new" in text
    assert "UNCHANGED=yes" in text
    assert "JPCORPUS_LLM_MODEL=Qwen/Qwen2.5-7B-Instruct" in text
    assert config["llm"]["provider"] == "openai-compatible"
    assert llm_config_status()["api_key_configured"] is True
