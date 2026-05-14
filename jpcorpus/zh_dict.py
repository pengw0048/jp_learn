from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from .paths import DEFAULT_ZH_DICT, ensure_parent


DEFAULT_ZH_DICT_URL = (
    "https://raw.githubusercontent.com/lxl66566/"
    "Japanese-Chinese-thesaurus/main/final.json"
)
CHINESE_GLOSS_OVERRIDES = {
    "ありがとう": "谢谢",
    "有難う": "谢谢",
    "有り難う": "谢谢",
    "おはよう": "早上好",
    "お早う": "早上好",
    "こんにちは": "你好；午安",
    "こんばんは": "晚上好",
    "ごめんなさい": "对不起；不好意思",
    "すみません": "不好意思；对不起；劳驾",
    "さようなら": "再见",
    "いただきます": "我开动了；饭前致谢",
    "ごちそうさま": "多谢款待；我吃好了",
    "お休み": "晚安；休息",
    "おやすみ": "晚安；休息",
}


@dataclass(frozen=True)
class ChineseGlossary:
    entries: dict[str, str]

    @classmethod
    def load(cls, path: Path = DEFAULT_ZH_DICT) -> "ChineseGlossary":
        if not path.exists():
            return cls({})
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Chinese glossary must be a JSON object: {path}")
        entries = {str(key): clean_gloss(str(value)) for key, value in payload.items()}
        entries.update(CHINESE_GLOSS_OVERRIDES)
        return cls(entries)

    def lookup(self, *keys: str | None) -> str | None:
        for key in keys:
            if not key:
                continue
            gloss = self.entries.get(key)
            if gloss:
                return gloss
        return None


def download_zh_dict(
    path: Path = DEFAULT_ZH_DICT,
    *,
    source_url: str = DEFAULT_ZH_DICT_URL,
    timeout: float = 60.0,
) -> Path:
    ensure_parent(path)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.get(source_url)
        response.raise_for_status()
    payload: Any = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Downloaded Chinese glossary is not a JSON object.")
    normalized = {str(key): clean_gloss(str(value)) for key, value in payload.items()}
    path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def clean_gloss(value: str) -> str:
    value = value.replace("\\n", " ")
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"^[（(][ぁ-んァ-ンー・\s0-9０-９⓪①②③④⑤⑥⑦⑧⑨/／;；]+[）)]\s*", "", value)
    return value
