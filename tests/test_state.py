from pathlib import Path

from jpcorpus.models import WatchedShow
from jpcorpus.state import State


def test_state_attaches_cached_bangumi_character_names_to_subtitles(tmp_path: Path):
    state = State(tmp_path / "state.db")
    subtitle = tmp_path / "show.srt"
    subtitle.write_text("1\n00:00:01,000 --> 00:00:02,000\nテスト\n", encoding="utf-8")
    state.save_watched_show(
        WatchedShow(
            bangumi_id=100444,
            title_jp="四月は君の嘘",
            title_zh="四月是你的谎言",
            subject={},
            collection={},
        )
    )
    state.save_show_characters(
        100444,
        [{"id": 26006, "name": "相座武士", "relation": "配角"}],
    )
    state.save_subtitle_file(
        bangumi_id=100444,
        jimaku_entry_id=None,
        episode=1,
        name="show.srt",
        url=None,
        size=subtitle.stat().st_size,
        local_path=subtitle,
    )

    [subtitle_file] = state.list_subtitle_files()

    assert subtitle_file.show_characters == ["相座武士"]
