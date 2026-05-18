from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from .paths import APP_DIR, ensure_parent


DEFAULT_VIEWER_STUDY_STATE = APP_DIR / "viewer-study-state.json"
STUDY_STATUS_VALUES = {"none", "learning", "known"}
STUDY_TARGET_COUNT = 7


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def viewer_study_state(*, path: Path | None = None) -> dict[str, Any]:
    return normalize_viewer_study_state(read_viewer_study_state(path=path))


def save_viewer_study_state(raw: dict[str, Any], *, path: Path | None = None) -> dict[str, Any]:
    state = normalize_viewer_study_state(raw)
    state["updated_at"] = _now_iso()
    write_viewer_study_state(state, path=path)
    return state


def update_viewer_word_status(raw: dict[str, Any], *, path: Path | None = None) -> dict[str, Any]:
    word = text_limit(raw.get("word"), 120).strip()
    if not word:
        raise ValueError("word is required.")
    status = str(raw.get("status") or "learning").strip()
    if status not in STUDY_STATUS_VALUES:
        raise ValueError(f"Unsupported word status: {status}")

    state = normalize_viewer_study_state(read_viewer_study_state(path=path))
    statuses = state["statuses"]
    counts = state["study_counts"]
    schedule = state["study_schedule"]

    if status == "none":
        statuses.pop(word, None)
        counts.pop(word, None)
        schedule.pop(word, None)
    else:
        statuses[word] = status
        if status == "known":
            counts[word] = STUDY_TARGET_COUNT
            schedule.pop(word, None)
        elif status == "learning":
            count = clamp_study_count(raw.get("study_count", counts.get(word, 0)))
            if count > 0:
                counts[word] = count
            else:
                counts.pop(word, None)
            raw_schedule = raw.get("study_schedule")
            schedule[word] = (
                normalize_study_schedule({word: raw_schedule}).get(word)
                if isinstance(raw_schedule, dict)
                else None
            ) or {
                "last_seen": today_key(),
                "due_date": add_days_key(today_key(), 1),
            }

    state["updated_at"] = _now_iso()
    write_viewer_study_state(state, path=path)
    return {
        "word": word,
        "status": study_status_for_word(word, state),
        "study_count": counts.get(word, 0),
        "study_schedule": schedule.get(word),
        "state": state,
    }


def read_viewer_study_state(*, path: Path | None = None) -> dict[str, Any]:
    target = path or DEFAULT_VIEWER_STUDY_STATE
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def write_viewer_study_state(state: dict[str, Any], *, path: Path | None = None) -> None:
    target = path or DEFAULT_VIEWER_STUDY_STATE
    ensure_parent(target)
    payload = normalize_viewer_study_state(state)
    payload["updated_at"] = str(payload.get("updated_at") or _now_iso())
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_viewer_study_state(raw: dict[str, Any]) -> dict[str, Any]:
    statuses = raw.get("statuses") if isinstance(raw, dict) else {}
    study_counts = raw.get("study_counts") if isinstance(raw, dict) else {}
    study_schedule = raw.get("study_schedule") if isinstance(raw, dict) else {}
    return {
        "statuses": normalize_status_map(statuses),
        "study_counts": normalize_study_counts(study_counts),
        "study_schedule": normalize_study_schedule(study_schedule),
        "updated_at": str(raw.get("updated_at") or "") if isinstance(raw, dict) else "",
    }


def normalize_status_map(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, str] = {}
    for word, status in value.items():
        word_text = text_limit(word, 120).strip()
        status_text = str(status or "").strip()
        if word_text and status_text in STUDY_STATUS_VALUES and status_text != "none":
            normalized[word_text] = status_text
    return normalized


def normalize_study_counts(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, int] = {}
    for word, count in value.items():
        word_text = text_limit(word, 120).strip()
        count_value = clamp_study_count(count)
        if word_text and count_value > 0:
            normalized[word_text] = count_value
    return normalized


def normalize_study_schedule(value: Any) -> dict[str, dict[str, str]]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, dict[str, str]] = {}
    for word, schedule in value.items():
        if not isinstance(schedule, dict):
            continue
        word_text = text_limit(word, 120).strip()
        if not word_text:
            continue
        last_seen = str(schedule.get("last_seen") or "")
        due_date = str(schedule.get("due_date") or today_key())
        normalized[word_text] = {
            "last_seen": last_seen,
            "due_date": due_date,
        }
    return normalized


def clamp_study_count(value: Any) -> int:
    try:
        count = int(value)
    except (TypeError, ValueError):
        return 0
    if count <= 0:
        return 0
    return min(count, STUDY_TARGET_COUNT)


def study_status_for_word(word: str, state: dict[str, Any]) -> str:
    statuses = state.get("statuses") if isinstance(state, dict) else {}
    counts = state.get("study_counts") if isinstance(state, dict) else {}
    status = statuses.get(word) if isinstance(statuses, dict) else None
    if status in {"known", "learning"}:
        return status
    count = clamp_study_count(counts.get(word) if isinstance(counts, dict) else 0)
    if count >= STUDY_TARGET_COUNT:
        return "known"
    if count > 0:
        return "learning"
    return "none"


def today_key(date: datetime | None = None) -> str:
    value = date or datetime.now()
    return value.strftime("%Y-%m-%d")


def add_days_key(date_key: str, days: int) -> str:
    try:
        value = datetime.strptime(date_key, "%Y-%m-%d")
    except ValueError:
        value = datetime.now()
    return (value + timedelta(days=days)).strftime("%Y-%m-%d")


def text_limit(value: Any, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."
