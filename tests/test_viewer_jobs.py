import pytest

from jpcorpus.viewer_jobs import maintenance_command, normalize_maintenance_spec


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
