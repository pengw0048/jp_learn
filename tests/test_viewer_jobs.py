import pytest

from jpcorpus.viewer_jobs import (
    composite_maintenance_steps,
    maintenance_command,
    normalize_maintenance_spec,
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

    assert [step[1]["type"] for step in steps[:3]] == [
        "fetch_anime_db",
        "fetch_zh_dict",
        "fetch_jlpt_words",
    ]
    assert steps[-1][1]["type"] == "export_corpus"
