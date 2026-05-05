from pathlib import Path

from jpcorpus.bangumi import collection_to_music_tracks
from jpcorpus.lyrics import (
    is_probably_instrumental_title,
    parse_lrc_text,
    score_lrclib_result,
    write_lrclib_lyric,
)
from jpcorpus.models import LyricFile, MusicTrack
from jpcorpus.state import State


def test_parse_lrc_text_preserves_timed_japanese_lines():
    lines = parse_lrc_text(
        "[00:01.00]約束を見ている\n"
        "[00:04.50]not japanese\n"
        "[00:07.25]微妙な気持ち\n"
    )

    assert [line.text for line in lines] == ["約束を見ている", "微妙な気持ち"]
    assert lines[0].start_ms == 1000
    assert lines[0].end_ms == 7250
    assert lines[1].start_ms == 7250


def test_lrclib_scoring_prefers_synced_japanese_exact_title():
    track = MusicTrack(
        track_key="track-1",
        bangumi_id=1,
        title="鳥の詩",
        album_title="AIR",
        artist="Lia",
    )

    score = score_lrclib_result(
        track,
        {
            "trackName": "鳥の詩",
            "artistName": "Lia",
            "syncedLyrics": "[00:01.00]消える飛行機雲\n",
            "plainLyrics": "消える飛行機雲",
        },
    )

    assert score > 15


def test_write_lrclib_lyric_uses_local_cache(tmp_path: Path):
    track = MusicTrack(
        track_key="bangumi:1:ep:2",
        bangumi_id=1,
        title="だんご大家族",
        album_title="CLANNAD",
    )

    lyric_file = write_lrclib_lyric(
        track,
        {"id": 123, "plainLyrics": "だんご だんご\n"},
        cache_dir=tmp_path,
    )

    assert lyric_file.provider == "lrclib"
    assert lyric_file.source_id == "123"
    assert lyric_file.path.exists()
    assert lyric_file.path.read_text(encoding="utf-8") == "だんご だんご\n"


def test_instrumental_title_detection():
    assert is_probably_instrumental_title("only my railgun-instrumental-")
    assert is_probably_instrumental_title("鳥の詩 off vocal")
    assert not is_probably_instrumental_title("鳥の詩")


def test_bangumi_music_collection_splits_album_tracks():
    tracks = collection_to_music_tracks(
        {
            "subject_id": 7733,
            "subject": {
                "id": 7733,
                "name": "新世紀エヴァンゲリオン",
                "infobox": [{"key": "artist", "value": "高橋洋子"}],
            },
        },
        [
            {"id": 44870, "name": "残酷な天使のテーゼ", "sort": 1},
            {"id": 44871, "name": "FLY ME TO THE MOON", "sort": 2},
        ],
    )

    assert [track.title for track in tracks] == ["残酷な天使のテーゼ", "FLY ME TO THE MOON"]
    assert tracks[0].track_key == "bangumi:7733:ep:44870"
    assert tracks[0].artist == "高橋洋子"
    assert tracks[1].track_number == 2


def test_state_caches_lyric_misses_until_a_file_is_saved(tmp_path: Path):
    state = State(tmp_path / "state.db")
    track = MusicTrack(
        track_key="track-1",
        bangumi_id=1,
        title="汐",
        album_title="CLANNAD",
    )
    state.save_music_track(track)

    state.save_lyric_miss(
        track_key=track.track_key,
        provider="lrclib",
        reason="not_found",
    )

    assert state.list_lyric_miss_keys(provider="lrclib") == {"track-1"}
    assert state.count_lyric_misses(provider="lrclib") == 1

    state.save_lyric_file(
        LyricFile(
            track_key=track.track_key,
            bangumi_id=track.bangumi_id,
            track_title=track.title,
            album_title=track.album_title,
            path=tmp_path / "track.lrc",
            provider="lrclib",
        )
    )

    assert state.list_lyric_miss_keys(provider="lrclib") == set()
