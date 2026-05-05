from pathlib import Path

from jpcorpus.bangumi import collection_to_music_tracks
from jpcorpus.lyrics import (
    artist_candidates,
    is_probably_instrumental_title,
    lyric_album_search_params,
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


def test_artist_candidates_split_bangumi_album_artists():
    track = MusicTrack(
        track_key="track-1",
        bangumi_id=1,
        title="メグメル",
        album_title="CLANNAD",
        artist="eufonius、茶太、riya",
    )

    assert artist_candidates(track)[:3] == ["eufonius", "茶太", "riya"]


def test_album_search_params_start_specific_then_fallback():
    params = lyric_album_search_params("only my railgun", ["fripSide"])

    assert params == [
        {
            "q": "only my railgun",
            "album_name": "only my railgun",
            "artist_name": "fripSide",
        },
        {"q": "only my railgun", "album_name": "only my railgun"},
        {"q": "only my railgun"},
    ]


def test_lrclib_scoring_rejects_short_title_without_artist_or_album_match():
    track = MusicTrack(
        track_key="track-1",
        bangumi_id=1,
        title="渚",
        album_title="CLANNAD Original SoundTrack",
        artist="riya",
    )

    score = score_lrclib_result(
        track,
        {
            "trackName": "渚",
            "artistName": "SPITZ",
            "albumName": "インディゴ地平線",
            "syncedLyrics": "[00:01.00]ささやく冗談でいつも\n",
        },
    )

    assert score == 0


def test_lrclib_scoring_rejects_non_japanese_lyrics():
    track = MusicTrack(
        track_key="track-1",
        bangumi_id=1,
        title="幻想",
        album_title="CLANNAD Original SoundTrack",
        artist="riya",
    )

    score = score_lrclib_result(
        track,
        {
            "trackName": "幻想",
            "artistName": "張學友",
            "albumName": "這個冬天不太冷",
            "syncedLyrics": "[00:01.00]一生一火花\n",
        },
    )

    assert score == 0


def test_lrclib_scoring_rejects_result_off_vocal():
    track = MusicTrack(
        track_key="track-1",
        bangumi_id=1,
        title="secret base ~君がくれたもの~ (Memento mori Ver.)",
        album_title="secret base ～君がくれたもの～",
        artist="茅野愛衣",
    )

    score = score_lrclib_result(
        track,
        {
            "trackName": "secret base ～君がくれたもの～ (Memento mori Ver.) (Off Vocal Version)",
            "artistName": "Meiko Honma (CV:Ai Kayano)",
            "albumName": "secret base ～君がくれたもの～",
            "plainLyrics": "君と夏の終わり\n",
        },
    )

    assert score == 0


def test_lrclib_scoring_allows_cover_when_title_is_exact():
    track = MusicTrack(
        track_key="track-1",
        bangumi_id=1,
        title="FLY ME TO THE MOON",
        album_title="残酷な天使のテーゼ / FLY ME TO THE MOON",
        artist="高橋洋子 / CLAIRE",
    )

    score = score_lrclib_result(
        track,
        {
            "trackName": "Fly Me to the Moon",
            "artistName": "春奈るな",
            "albumName": "LUNARIUM",
            "syncedLyrics": "[00:01.00]私を月に連れてって\n",
        },
    )

    assert score > 10


def test_lrclib_scoring_allows_remix_when_title_is_partial():
    track = MusicTrack(
        track_key="track-1",
        bangumi_id=1,
        title="願いが叶う場所",
        album_title="CLANNAD Original SoundTrack",
        artist="Lia / riya",
    )

    score = score_lrclib_result(
        track,
        {
            "trackName": "願いが叶う場所(JAKAZiD's Nu Hardcore Breaks Mix)",
            "artistName": "Lia",
            "albumName": "enigmatic LIA4",
            "plainLyrics": "願いが叶う場所へ\n",
        },
    )

    assert score > 0


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
