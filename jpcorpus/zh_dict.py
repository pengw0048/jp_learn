from __future__ import annotations

from functools import lru_cache
import gzip
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import httpx
from opencc import OpenCC

from .paths import DEFAULT_ZH_DICT, DEFAULT_ZHWIKTIONARY_JA_DICT, DEFAULT_ZHWIKTIONARY_RAW, ensure_parent


DEFAULT_ZH_DICT_URL = (
    "https://raw.githubusercontent.com/lxl66566/"
    "Japanese-Chinese-thesaurus/main/final.json"
)
ZHWIKTIONARY_RAW_URL = "https://kaikki.org/zhwiktionary/raw-wiktextract-data.jsonl.gz"
ZHWIKTIONARY_FORM_SKIP_TAGS = {"romanization", "past", "continuative", "archaic"}
ZHWIKTIONARY_POS_LABELS = {
    "noun": "名词",
    "名詞": "名词",
    "名词": "名词",
    "proper-noun": "专有名词",
    "verb": "动词",
    "動詞": "动词",
    "动词": "动词",
    "adj": "形容词",
    "adjective": "形容词",
    "形容詞": "形容词",
    "形容词": "形容词",
    "adv": "副词",
    "adverb": "副词",
    "副詞": "副词",
    "副词": "副词",
    "intj": "感叹词",
    "interjection": "感叹词",
    "感嘆詞": "感叹词",
    "感歎詞": "感叹词",
    "叹词": "感叹词",
    "suffix": "接尾词",
    "后缀": "接尾词",
    "接尾辞": "接尾词",
    "prefix": "接头词",
    "前缀": "接头词",
    "接頭辞": "接头词",
}
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
    readings: dict[str, tuple[str, ...]] = field(default_factory=dict)
    parts_of_speech: dict[str, tuple[str, ...]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path = DEFAULT_ZH_DICT) -> "ChineseGlossary":
        paths = [path]
        if path == DEFAULT_ZH_DICT and DEFAULT_ZHWIKTIONARY_JA_DICT.exists():
            paths.append(DEFAULT_ZHWIKTIONARY_JA_DICT)
        entries: dict[str, str] = {}
        readings: dict[str, tuple[str, ...]] = {}
        parts_of_speech: dict[str, tuple[str, ...]] = {}
        for glossary_path in paths:
            loaded_entries, loaded_readings, loaded_parts_of_speech = load_glossary_payload(glossary_path)
            entries.update(loaded_entries)
            for key in loaded_entries:
                entry_readings = loaded_readings.get(key)
                if entry_readings:
                    readings[key] = entry_readings
                else:
                    readings.pop(key, None)
                entry_parts_of_speech = loaded_parts_of_speech.get(key)
                if entry_parts_of_speech:
                    parts_of_speech[key] = entry_parts_of_speech
                else:
                    parts_of_speech.pop(key, None)
        entries.update(CHINESE_GLOSS_OVERRIDES)
        for key in CHINESE_GLOSS_OVERRIDES:
            readings.pop(key, None)
        return cls(entries, readings, parts_of_speech)

    def lookup(self, *keys: str | None, reading: str | None = None) -> str | None:
        for key in keys:
            if not key:
                continue
            gloss = self.entries.get(key)
            if gloss:
                expected_readings = self.readings.get(key)
                if expected_readings and reading and not readings_match(reading, expected_readings):
                    continue
                return gloss
        return None

    def lookup_parts_of_speech(self, *keys: str | None, reading: str | None = None) -> tuple[str, ...]:
        for key in keys:
            if not key:
                continue
            values = self.parts_of_speech.get(key)
            if values:
                expected_readings = self.readings.get(key)
                if expected_readings and reading and not readings_match(reading, expected_readings):
                    continue
                return values
        return ()


def load_glossary_payload(
    path: Path,
) -> tuple[dict[str, str], dict[str, tuple[str, ...]], dict[str, tuple[str, ...]]]:
    if not path.exists():
        return {}, {}, {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Chinese glossary must be a JSON object: {path}")
    entries: dict[str, str] = {}
    readings: dict[str, tuple[str, ...]] = {}
    parts_of_speech: dict[str, tuple[str, ...]] = {}
    for key, value in payload.items():
        key_text = str(key)
        if isinstance(value, dict):
            value_text = str(value.get("gloss") or "")
            entry_readings = tuple(str(item) for item in value.get("readings") or [] if str(item))
            entry_parts_of_speech = tuple(
                str(item) for item in value.get("parts_of_speech") or [] if str(item)
            )
        else:
            value_text = str(value)
            entry_readings = extract_gloss_readings(value_text)
            entry_parts_of_speech = ()
        entries[key_text] = clean_gloss(value_text)
        if entry_readings:
            readings[key_text] = entry_readings
        if entry_parts_of_speech:
            parts_of_speech[key_text] = entry_parts_of_speech
    return entries, readings, parts_of_speech


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
    normalized = {str(key): normalize_gloss_source(str(value)) for key, value in payload.items()}
    path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def download_zhwiktionary_ja_dict(
    output: Path = DEFAULT_ZHWIKTIONARY_JA_DICT,
    *,
    raw_path: Path = DEFAULT_ZHWIKTIONARY_RAW,
    source_url: str = ZHWIKTIONARY_RAW_URL,
    timeout: float = 300.0,
) -> Path:
    ensure_parent(raw_path)
    if not raw_path.exists():
        with httpx.stream("GET", source_url, timeout=timeout, follow_redirects=True) as response:
            response.raise_for_status()
            with raw_path.open("wb") as handle:
                for chunk in response.iter_bytes():
                    handle.write(chunk)
    return build_zhwiktionary_ja_dict(raw_path, output)


def build_zhwiktionary_ja_dict(raw_path: Path, output: Path = DEFAULT_ZHWIKTIONARY_JA_DICT) -> Path:
    entries: dict[str, dict[str, Any]] = {}
    opener = gzip.open if raw_path.suffix == ".gz" else open
    with opener(raw_path, "rt", encoding="utf-8") as handle:
        for line in handle:
            raw = line.strip()
            if not raw:
                continue
            item = json.loads(raw)
            entry = zhwiktionary_ja_entry(item)
            if not entry:
                continue
            for key in zhwiktionary_ja_keys(item):
                current = entries.get(key)
                if current is None or int(entry["score"]) > int(current.get("score") or 0):
                    entries[key] = entry
    payload = {
        key: {
            "gloss": value["gloss"],
            "readings": value.get("readings") or [],
            "parts_of_speech": value.get("parts_of_speech") or [],
        }
        for key, value in sorted(entries.items())
    }
    ensure_parent(output)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def zhwiktionary_ja_entry(item: dict[str, Any]) -> dict[str, Any] | None:
    if item.get("lang_code") != "ja":
        return None
    pos = str(item.get("pos") or "")
    pos_title = str(item.get("pos_title") or "")
    if pos in {"character", "syllable", "soft-redirect"} or pos_title in {"漢字", "平假名", "片假名"}:
        return None
    sense_glosses = zhwiktionary_sense_glosses(item)
    if not sense_glosses:
        return None
    readings = zhwiktionary_readings(item)
    parts_of_speech = zhwiktionary_parts_of_speech(item)
    return {
        "gloss": "；".join(sense_glosses[:5]),
        "readings": readings,
        "parts_of_speech": parts_of_speech,
        "score": zhwiktionary_entry_score(item, readings),
    }


def zhwiktionary_sense_glosses(item: dict[str, Any]) -> list[str]:
    primary: list[str] = []
    secondary: list[str] = []
    for sense in item.get("senses") or []:
        if not isinstance(sense, dict) or "no-gloss" in (sense.get("tags") or []):
            continue
        glosses = [
            clean_zhwiktionary_gloss(str(value))
            for value in sense.get("glosses") or []
            if str(value).strip()
        ]
        if not glosses:
            continue
        tags = set(str(tag) for tag in (sense.get("tags") or []))
        raw_tags = set(str(tag) for tag in (sense.get("raw_tags") or []))
        target = secondary if tags & {"archaic", "obsolete", "rare"} or raw_tags & {"罕用", "古舊", "古典日語"} else primary
        target.append("，".join(glosses[:3]))
    return unique_strings(primary or secondary)


def zhwiktionary_readings(item: dict[str, Any]) -> list[str]:
    word = str(item.get("word") or "")
    values: list[str] = []
    if is_kanaish(word):
        values.append(katakana_to_hiragana(word))
    for form in item.get("forms") or []:
        if not isinstance(form, dict):
            continue
        form_text = str(form.get("form") or "")
        tags = set(str(tag) for tag in (form.get("tags") or []))
        if is_kanaish(form_text) and not tags & ZHWIKTIONARY_FORM_SKIP_TAGS:
            values.append(katakana_to_hiragana(form_text))
    return unique_strings(values)


def zhwiktionary_parts_of_speech(item: dict[str, Any]) -> list[str]:
    return unique_strings(
        label
        for value in (item.get("pos"), item.get("pos_title"))
        if (label := ZHWIKTIONARY_POS_LABELS.get(str(value or "")))
    )


def zhwiktionary_ja_keys(item: dict[str, Any]) -> list[str]:
    values = [str(item.get("word") or "")]
    for form in item.get("forms") or []:
        if not isinstance(form, dict):
            continue
        form_text = str(form.get("form") or "")
        tags = set(str(tag) for tag in (form.get("tags") or []))
        if form_text and not tags & ZHWIKTIONARY_FORM_SKIP_TAGS:
            values.append(form_text)
    return unique_strings(value for value in values if value)


def zhwiktionary_entry_score(item: dict[str, Any], readings: list[str]) -> int:
    score = 10
    if readings:
        score += 3
    pos = str(item.get("pos") or "")
    if pos in {"noun", "verb", "adj", "adv"}:
        score += 2
    return score


def is_kanaish(value: str) -> bool:
    return bool(value) and all(("ぁ" <= char <= "ゖ") or ("ァ" <= char <= "ヺ") or char in "ー・" for char in value)


def unique_strings(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def normalize_gloss_source(value: str) -> str:
    value = value.replace("\\n", " ")
    return re.sub(r"\s+", " ", value).strip()


def clean_zhwiktionary_gloss(value: str) -> str:
    lines = [
        simplify_zh_gloss(normalize_gloss_source(line))
        for line in value.replace("\\n", "\n").splitlines()
        if line.strip()
    ]
    if len(lines) > 1:
        line_glosses = zhwiktionary_definition_lines(lines)
        if line_glosses:
            return "；".join(line_glosses)
    value = simplify_zh_gloss(normalize_gloss_source(value))
    value = strip_japanese_form_prefix(value)
    return strip_inline_japanese_example(value)


def zhwiktionary_definition_lines(lines: list[str]) -> list[str]:
    glosses: list[str] = []
    skip_example_translation = False
    for line in lines:
        line = strip_japanese_form_prefix(line)
        line = strip_zhwiktionary_headword_prefix(line)
        line = strip_zhwiktionary_pos_prefix(line)
        line = strip_numbered_gloss_prefix(line)
        if not line:
            continue
        if is_japanese_example_line(line):
            skip_example_translation = True
            continue
        if skip_example_translation and is_likely_example_translation(line):
            skip_example_translation = False
            continue
        skip_example_translation = False
        line = strip_inline_japanese_example(line)
        if line:
            glosses.append(line)
    return unique_strings(glosses)


def strip_zhwiktionary_headword_prefix(value: str) -> str:
    return re.sub(
        r"^.+?(?:【[ぁ-ゖァ-ヺー・/／;；\s]+】)+\s*",
        "",
        value,
        count=1,
    ).strip()


def strip_zhwiktionary_pos_prefix(value: str) -> str:
    return re.sub(
        r"^(?:名(?:[?？·・](?:副|形动|他サ|自サ))?|动|他动|自动|形动|形|副|连体|词组|惯用|接头|接尾|感|代|助动|助词|格助|终助|副助)(?:\s+|$)",
        "",
        value,
        count=1,
    ).strip()


def strip_numbered_gloss_prefix(value: str) -> str:
    return re.sub(r"^\d+[.．、]\s*", "", value, count=1).strip()


def strip_inline_japanese_example(value: str) -> str:
    parts = re.split(r"(?<=[。！？!?])\s+", value)
    if len(parts) <= 1:
        return value
    kept: list[str] = []
    for index, part in enumerate(parts):
        if index > 0 and starts_with_japanese_example(part):
            break
        kept.append(part)
    return " ".join(kept).strip()


def strip_japanese_form_prefix(value: str) -> str:
    match = re.match(r"^([^:：]{1,60})[：:]\s*(.+)$", value)
    if not match:
        return value
    prefix = match.group(1)
    if not contains_kana(prefix):
        return value
    return match.group(2).strip()


def contains_kana(value: str) -> bool:
    return bool(re.search(r"[ぁ-ゖァ-ヺ]", value))


def is_japanese_example_line(value: str) -> bool:
    if not contains_kana(value):
        return False
    if re.search(r"(的|义|语|词|谦|称|表示|用于|源于|简称|读作)", value):
        return False
    return True


def starts_with_japanese_example(value: str) -> bool:
    first_chunk = re.split(r"\s+", value.strip(), maxsplit=1)[0]
    return is_japanese_example_line(first_chunk)


def is_likely_example_translation(value: str) -> bool:
    return not contains_kana(value)


def simplify_zh_gloss(value: str) -> str:
    return opencc_t2s().convert(value)


@lru_cache(maxsize=1)
def opencc_t2s() -> OpenCC:
    return OpenCC("t2s")


def extract_gloss_readings(value: str) -> tuple[str, ...]:
    value = normalize_gloss_source(value)
    match = re.match(r"^[（(]([ぁ-んァ-ンー・\s0-9０-９⓪①②③④⑤⑥⑦⑧⑨/／;；]+)[）)]", value)
    if not match:
        return ()
    return split_readings(match.group(1))


def readings_match(reading: str, expected_readings: tuple[str, ...]) -> bool:
    normalized = set(split_readings(reading))
    expected = {katakana_to_hiragana(value) for value in expected_readings}
    return bool(normalized & expected)


def split_readings(value: str) -> tuple[str, ...]:
    readings: list[str] = []
    for item in re.split(r"[/／;；]", value):
        cleaned = re.sub(r"[0-9０-９⓪①②③④⑤⑥⑦⑧⑨\s]+", "", item)
        if cleaned:
            readings.append(katakana_to_hiragana(cleaned))
    return tuple(dict.fromkeys(readings))


def katakana_to_hiragana(value: str) -> str:
    return "".join(
        chr(ord(char) - 0x60) if "ァ" <= char <= "ヶ" else char
        for char in str(value or "")
    )


def clean_gloss(value: str) -> str:
    value = normalize_gloss_source(value)
    value = re.sub(r"^[（(][ぁ-んァ-ンー・\s0-9０-９⓪①②③④⑤⑥⑦⑧⑨/／;；]+[）)]\s*", "", value)
    return value
