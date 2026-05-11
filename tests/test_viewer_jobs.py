import pytest

from jpcorpus.viewer_jobs import (
    ViewerJob,
    ViewerJobRunner,
    build_annotation_predicate,
    composite_maintenance_steps,
    explain_reader_usage,
    llm_config_status,
    normalize_annotation_spec,
    normalize_maintenance_spec,
    public_annotation_spec,
    save_viewer_config,
    viewer_config_status,
)


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


def test_selected_examples_annotation_scope_matches_exact_example():
    target = {
        "source_type": "subtitle",
        "source_title": "CLANNAD",
        "subtitle_file": "clannad_ep05.srt",
        "episode": 5,
        "start_ms": 705240,
        "end_ms": 709000,
        "matched_text": "届か",
        "sentence": "声が届かないから、風子はこうしてるんだと思います",
    }
    spec = normalize_annotation_spec(
        {
            "scope": "selected_examples",
            "provider": "openai-compatible",
            "words": ["届く"],
            "examples": [target],
            "cache_only": False,
            "bypass_cache": True,
            "overwrite": True,
        }
    )

    include_example = build_annotation_predicate(spec)

    assert spec["bypass_cache"] is True
    assert public_annotation_spec(spec)["example_count"] == 1
    assert include_example({"word": "届く", "level": "N4"}, target)
    assert not include_example({"word": "届く", "level": "N4"}, {**target, "start_ms": 705241})
    assert not include_example({"word": "届ける", "level": "N4"}, target)


def test_annotation_spec_uses_configured_provider_when_request_omits_provider(monkeypatch):
    monkeypatch.setenv("JPCORPUS_LLM_PROVIDER", "anthropic")

    spec = normalize_annotation_spec({"scope": "first_unannotated"})

    assert spec["provider"] == "anthropic"


def test_selected_examples_annotation_scope_requires_examples():
    with pytest.raises(ValueError, match="requires at least one example"):
        normalize_annotation_spec(
            {
                "scope": "selected_examples",
                "provider": "openai-compatible",
                "words": ["届く"],
                "examples": [],
            }
        )


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

    monkeypatch.setattr("jpcorpus.cli.fetch_lyrics", fake_fetch_lyrics)
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

    monkeypatch.setattr("jpcorpus.cli.sync", fake_sync)
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

    monkeypatch.setattr("jpcorpus.cli.fetch_lexical_resources", fake_fetch_lexical_resources)
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


def test_explain_reader_usage_calls_llm_without_cache(monkeypatch):
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

    def fake_runtime(spec):
        calls["spec"] = spec
        return {}, FakeClient()

    monkeypatch.setattr("jpcorpus.viewer_jobs.resolve_annotation_runtime", fake_runtime)

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

    assert calls["spec"]["cache_only"] is False
    assert calls["spec"]["provider"] == "apple"
    assert calls["word"]["word"] == "行く"
    assert calls["example"]["sentence"] == "学校へ行く。"
    assert calls["closed"] is True
    assert result["explanation"]["usage_note_zh"] == "这里的「行く」表示移动到某处。"


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
