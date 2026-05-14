from __future__ import annotations

import os
from pathlib import Path


APP_DIR = Path(os.environ.get("JPCORPUS_HOME", Path.home() / ".jpcorpus"))
DEFAULT_STATE_DB = APP_DIR / "state.db"
DEFAULT_DATA_DIR = Path("data")
DEFAULT_ANIME_DB = DEFAULT_DATA_DIR / "anime-offline-database.json"
DEFAULT_JLPT_WORDS = DEFAULT_DATA_DIR / "jlpt-words.json"
DEFAULT_ZH_DICT = DEFAULT_DATA_DIR / "jp-zh-dict.json"
DEFAULT_ZHWIKTIONARY_JA_DICT = DEFAULT_DATA_DIR / "zhwiktionary-ja-dict.json"
DEFAULT_ZHWIKTIONARY_RAW = DEFAULT_DATA_DIR / "zhwiktionary-raw.jsonl.gz"
DEFAULT_JMDICT = DEFAULT_DATA_DIR / "JMdict_e.gz"
DEFAULT_KANJIDIC2 = DEFAULT_DATA_DIR / "kanjidic2.xml.gz"
DEFAULT_JIMAKU_CACHE = DEFAULT_DATA_DIR / "jimaku-cache"
DEFAULT_LYRICS_CACHE = DEFAULT_DATA_DIR / "lyrics-cache"
DEFAULT_TEXTS_DIR = Path("texts")


def ensure_parent(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
