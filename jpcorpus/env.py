from __future__ import annotations

import os
from pathlib import Path


def load_dotenv(path: Path | str = ".env", *, override: bool = False) -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = _strip_value(value.strip())
        if not key or (key in os.environ and not override):
            continue
        os.environ[key] = value


def _strip_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    comment_index = _inline_comment_index(value)
    if comment_index is not None:
        value = value[:comment_index].rstrip()
    return value


def _inline_comment_index(value: str) -> int | None:
    for index, char in enumerate(value):
        if char == "#" and (index == 0 or value[index - 1].isspace()):
            return index
    return None

