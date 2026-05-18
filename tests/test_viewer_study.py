from jpcorpus.viewer_study import (
    STUDY_TARGET_COUNT,
    normalize_viewer_study_state,
    read_viewer_study_state,
    update_viewer_word_status,
    viewer_study_state,
)


def test_normalize_viewer_study_state_filters_invalid_values():
    state = normalize_viewer_study_state(
        {
            "statuses": {
                "行く": "learning",
                "良い": "known",
                "old_uncertain": "uncertain",
                "old_ignored": "ignored",
                "bad": "wat",
            },
            "study_counts": {"行く": "2", "多い": 99, "bad": -1},
            "study_schedule": {
                "行く": {"last_seen": "2026-05-14", "due_date": "2026-05-15"},
                "bad": "not a schedule",
            },
        }
    )

    assert state["statuses"] == {"行く": "learning", "良い": "known"}
    assert state["study_counts"] == {"行く": 2, "多い": STUDY_TARGET_COUNT}
    assert state["study_schedule"] == {
        "行く": {"last_seen": "2026-05-14", "due_date": "2026-05-15"}
    }


def test_update_viewer_word_status_writes_to_given_path(tmp_path):
    path = tmp_path / "study.json"

    learning = update_viewer_word_status(
        {
            "word": "行く",
            "status": "learning",
            "study_count": 2,
            "study_schedule": {"last_seen": "2026-05-14", "due_date": "2026-05-15"},
        },
        path=path,
    )
    assert learning["status"] == "learning"
    assert learning["study_count"] == 2
    assert viewer_study_state(path=path)["statuses"]["行く"] == "learning"

    known = update_viewer_word_status({"word": "行く", "status": "known"}, path=path)
    assert known["status"] == "known"
    assert known["study_count"] == STUDY_TARGET_COUNT
    assert "行く" not in known["state"]["study_schedule"]

    cleared = update_viewer_word_status({"word": "行く", "status": "none"}, path=path)
    assert cleared["status"] == "none"
    assert read_viewer_study_state(path=path)["statuses"] == {}


def test_update_viewer_word_status_rejects_removed_statuses(tmp_path):
    path = tmp_path / "study.json"

    for status in ["uncertain", "ignored"]:
        try:
            update_viewer_word_status({"word": "行く", "status": status}, path=path)
        except ValueError as error:
            assert "Unsupported word status" in str(error)
        else:
            raise AssertionError(f"{status} should not be accepted")
