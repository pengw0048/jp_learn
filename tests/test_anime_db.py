from jpcorpus.anime_db import AnimeOfflineIndex, AnimeRecord, normalize_title
from jpcorpus.models import ExternalIds, WatchedShow


def test_normalize_title_removes_punctuation_and_width():
    assert normalize_title("ぼっち・ざ・ろっく！") == "ぼっちざろっく"


def test_match_show_by_title_and_year():
    index = AnimeOfflineIndex(
        [
            AnimeRecord(
                title="Bocchi the Rock!",
                synonyms=("ぼっち・ざ・ろっく！",),
                year=2022,
                episodes=12,
                ids=ExternalIds(mal_id=47917, anilist_id=130003),
            )
        ]
    )
    show = WatchedShow(
        bangumi_id=328609,
        title_jp="ぼっち・ざ・ろっく！",
        year=2022,
        subject={"eps": 12},
    )

    match = index.match_show(show)

    assert match is not None
    assert match.ids.anilist_id == 130003

