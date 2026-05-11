import pytest

from jpcorpus.viewer_jobs import (
    build_annotation_predicate,
    composite_maintenance_steps,
    llm_config_status,
    maintenance_command,
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


def test_maintenance_command_builds_fixed_fetch_lyrics_command(monkeypatch):
    monkeypatch.setattr("jpcorpus.viewer_jobs.jpcorpus_command", lambda: ["jpcorpus"])
    spec = normalize_maintenance_spec(
        {
            "type": "fetch_lyrics",
            "limit": 5,
            "concurrency": 3,
            "overwrite": True,
        }
    )

    assert maintenance_command(spec) == [
        "jpcorpus",
        "lyrics",
        "fetch",
        "--concurrency",
        "3",
        "--limit",
        "5",
        "--overwrite",
    ]


def test_maintenance_command_does_not_apply_limit_to_sync(monkeypatch):
    monkeypatch.setattr("jpcorpus.viewer_jobs.jpcorpus_command", lambda: ["jpcorpus"])
    spec = normalize_maintenance_spec({"type": "sync_anime", "limit": 3})

    assert maintenance_command(spec) == ["jpcorpus", "sync"]


def test_maintenance_command_can_fetch_lexical_resources(monkeypatch):
    monkeypatch.setattr("jpcorpus.viewer_jobs.jpcorpus_command", lambda: ["jpcorpus"])
    spec = normalize_maintenance_spec({"type": "fetch_lexical_resources"})

    assert maintenance_command(spec) == ["jpcorpus", "data", "fetch-lexical-resources"]


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
