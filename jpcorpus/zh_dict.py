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
ZH_DICT_POS_LABELS = {
    "名": "名词",
    "名词": "名词",
    "名詞": "名词",
    "专": "专有名词",
    "专有词": "专有名词",
    "代词": "代词",
    "动1": "动词",
    "动2": "动词",
    "动3": "动词",
    "動詞": "动词",
    "他动": "他动",
    "他动1": "他动",
    "他动2": "他动",
    "他动3": "他动",
    "自动": "自动",
    "自动1": "自动",
    "自动2": "自动",
    "自动3": "自动",
    "形1": "い形容词",
    "イ形": "い形容词",
    "形2": "な形容词",
    "ナ形": "な形容词",
    "形容词": "形容词",
    "形容动词": "な形容词",
    "自サ": "自动",
    "他サ": "他动",
    "自他サ": "自他动",
    "自动3": "自动",
    "他动3": "他动",
    "自他动3": "自他动",
    "副": "副词",
    "副词": "副词",
    "接续词": "接续词",
    "连接词": "接续词",
    "感叹词": "感叹词",
    "惯用语": "惯用语",
    "熟语": "惯用语",
}
CHINESE_GLOSS_OVERRIDES = {
    "ありがとう": "谢谢",
    "有難う": "谢谢",
    "有り難う": "谢谢",
    "おはよう": "早上好",
    "お早う": "早上好",
    "こんにちは": "你好；午安",
    "こんばんは": "晚上好",
    "ごめん": "对不起；不好意思",
    "ご免": "对不起；不好意思",
    "御免": "对不起；不好意思",
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
    fallback_entries: dict[str, str] = field(default_factory=dict)
    fallback_readings: dict[str, tuple[str, ...]] = field(default_factory=dict)
    fallback_parts_of_speech: dict[str, tuple[str, ...]] = field(default_factory=dict)
    source_by_key: dict[str, str] = field(default_factory=dict)
    fallback_source_by_key: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path = DEFAULT_ZH_DICT) -> "ChineseGlossary":
        paths = [path]
        if path == DEFAULT_ZH_DICT and DEFAULT_ZHWIKTIONARY_JA_DICT.exists():
            paths.append(DEFAULT_ZHWIKTIONARY_JA_DICT)
        entries: dict[str, str] = {}
        readings: dict[str, tuple[str, ...]] = {}
        parts_of_speech: dict[str, tuple[str, ...]] = {}
        fallback_entries: dict[str, str] = {}
        fallback_readings: dict[str, tuple[str, ...]] = {}
        fallback_parts_of_speech: dict[str, tuple[str, ...]] = {}
        source_by_key: dict[str, str] = {}
        fallback_source_by_key: dict[str, str] = {}
        for index, glossary_path in enumerate(paths):
            is_fallback = index > 0
            loaded_entries, loaded_readings, loaded_parts_of_speech = load_glossary_payload(glossary_path)
            for key, gloss in loaded_entries.items():
                entry_parts_of_speech = loaded_parts_of_speech.get(key)
                entry_readings = loaded_readings.get(key)
                if is_fallback:
                    fallback_entries[key] = gloss
                    fallback_source_by_key[key] = "zhwiktionary_fallback"
                    if entry_readings:
                        fallback_readings[key] = entry_readings
                    else:
                        fallback_readings.pop(key, None)
                    if entry_parts_of_speech:
                        fallback_parts_of_speech[key] = entry_parts_of_speech
                    else:
                        fallback_parts_of_speech.pop(key, None)
                if is_fallback and key in entries:
                    if entry_parts_of_speech and key not in parts_of_speech:
                        parts_of_speech[key] = entry_parts_of_speech
                    continue
                entries[key] = gloss
                source_by_key[key] = "zhwiktionary_fallback" if is_fallback else "zh_dict"
                if entry_readings:
                    readings[key] = entry_readings
                else:
                    readings.pop(key, None)
                if entry_parts_of_speech:
                    parts_of_speech[key] = entry_parts_of_speech
                else:
                    parts_of_speech.pop(key, None)
        entries.update(CHINESE_GLOSS_OVERRIDES)
        for key in CHINESE_GLOSS_OVERRIDES:
            source_by_key[key] = "override"
            readings.pop(key, None)
        return cls(
            entries,
            readings,
            parts_of_speech,
            fallback_entries,
            fallback_readings,
            fallback_parts_of_speech,
            source_by_key,
            fallback_source_by_key,
        )

    def lookup(self, *keys: str | None, reading: str | None = None) -> str | None:
        result = self.lookup_with_source(*keys, reading=reading)
        return result[0] if result else None

    def lookup_with_source(self, *keys: str | None, reading: str | None = None) -> tuple[str, str] | None:
        for key in keys:
            if not key:
                continue
            result = lookup_gloss_entry(
                self.entries,
                self.readings,
                self.source_by_key,
                key,
                reading=reading,
                default_source="zh_dict",
            )
            if result:
                return result
            result = lookup_gloss_entry(
                self.fallback_entries,
                self.fallback_readings,
                self.fallback_source_by_key,
                key,
                reading=reading,
                default_source="zhwiktionary_fallback",
            )
            if result:
                return result
        return None

    def lookup_parts_of_speech(self, *keys: str | None, reading: str | None = None) -> tuple[str, ...]:
        for key in keys:
            if not key:
                continue
            values = lookup_tuple_entry(self.parts_of_speech, self.readings, key, reading=reading)
            if values:
                return values
            values = lookup_tuple_entry(
                self.fallback_parts_of_speech,
                self.fallback_readings,
                key,
                reading=reading,
            )
            if values:
                return values
        return ()


def lookup_gloss_entry(
    entries: dict[str, str],
    readings: dict[str, tuple[str, ...]],
    sources: dict[str, str],
    key: str,
    *,
    reading: str | None,
    default_source: str,
) -> tuple[str, str] | None:
    gloss = entries.get(key)
    if not gloss:
        return None
    if not entry_reading_matches(readings, key, reading=reading):
        return None
    return gloss, sources.get(key, default_source)


def lookup_tuple_entry(
    entries: dict[str, tuple[str, ...]],
    readings: dict[str, tuple[str, ...]],
    key: str,
    *,
    reading: str | None,
) -> tuple[str, ...]:
    values = entries.get(key)
    if not values:
        return ()
    if not entry_reading_matches(readings, key, reading=reading):
        return ()
    return values


def entry_reading_matches(
    readings: dict[str, tuple[str, ...]],
    key: str,
    *,
    reading: str | None,
) -> bool:
    expected_readings = readings.get(key)
    return not expected_readings or not reading or readings_match(reading, expected_readings)


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
            entry_parts_of_speech = extract_gloss_parts_of_speech(value_text)
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
        glosses: list[str] = []
        for value in sense.get("glosses") or []:
            if not str(value).strip():
                continue
            cleaned = clean_zhwiktionary_gloss(str(value))
            if cleaned:
                glosses.append(cleaned)
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
    return clean_zhwiktionary_inline_gloss(value)


def clean_zhwiktionary_inline_gloss(value: str) -> str:
    return "；".join(
        unique_strings(
            cleaned
            for part in re.split(r"[;；]", value)
            if (cleaned := clean_zhwiktionary_gloss_part(part))
        )
    )


def clean_zhwiktionary_gloss_part(value: str) -> str:
    value = normalize_gloss_source(value).strip(" 　；;")
    if not value or re.fullmatch(r"=+\s*日语\s*=+", value):
        return ""
    value = re.sub(r"=+\s*日语\s*=+\s*", "", value)
    value = strip_japanese_form_prefix(value)
    value = strip_zhwiktionary_headword_prefix(value)
    value = strip_parenthetical_headword_prefix(value)
    value = strip_zhwiktionary_headword_usage_prefix(value)
    value = strip_leading_japanese_usage_bracket(value)
    value = strip_latin_usage_bracket(value)
    value = strip_zhwiktionary_semantic_prefix(value)
    value = strip_zhwiktionary_pos_prefix(value)
    value = normalize_zhwiktionary_meta_gloss(value)
    value = strip_trailing_japanese_variant_note(value)
    value = strip_inline_japanese_example(value)
    value = value.strip(" 　，,；;")
    return "" if is_useless_zhwiktionary_gloss_part(value) else value


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
        line = clean_zhwiktionary_gloss_part(line)
        if not line:
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
    value = re.sub(
        r"^［[^］]*(?:名词|副词|动词|形容词)[^］]*］\s*",
        "",
        value,
        count=1,
    ).strip()
    pos_token = (
        r"(?:名|副|形动|形|动|他动|自动|自他|他|自|サ|五|下一|补动|连体|词组|惯用|接头|接尾|"
        r"感|代|助动|助词|格助|终助|副助)"
    )
    if re.fullmatch(rf"{pos_token}(?:[?？·・•.\s]*(?:{pos_token}))*", value):
        return ""
    return re.sub(
        rf"^(?:{pos_token}(?:[?？·・•.\s]*(?:{pos_token}))*)(?:\s+|$)",
        "",
        value,
        count=1,
    ).strip()


def strip_parenthetical_headword_prefix(value: str) -> str:
    return re.sub(
        r"^[一-龯々ぁ-ゖァ-ヺー・]+[（(][ぁ-ゖァ-ヺー・/／;；\s]+[）)](?:\s*[（(][^)）]+[）)])?\s*",
        "",
        value,
        count=1,
    ).strip()


def normalize_zhwiktionary_meta_gloss(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if match := re.match(r"^→[^，,；;]+[，,]\s*(.+)$", value):
        return match.group(1).strip()
    if match := re.search(r"[（(][^()（）]*[“\"]([^”\"]+)[”\"][^()（）]*[）)]", value):
        return match.group(1).strip()
    if match := re.match(r"^(.+?)的(?:另一种写法|旧字体形式|異體字|异体字|简写|简称|缩写|截断形式)[。.]?$", value):
        return clean_meta_gloss_target(match.group(1))
    if match := re.match(r"^.+?的(?:另一种写法|旧字体形式|異體字|异体字)[:：]\s*(.+)$", value):
        return match.group(1).strip()
    if re.match(r"^同[ぁ-ゖァ-ヺー・]+(?:\s*[（(][^)）]+[)）])?[。.]?$", value):
        return ""
    if (contains_kana(value) or contains_latin(value)) and re.search(
        r"(?:之|的)?(?:另一种写法|旧字体形式|简写|简称|缩写|截断形式|同义词)(?:[（(][^)）]+[)）])?[。.]?$",
        value,
    ):
        return ""
    if re.search(r"(?:后|後)接.+[:：]$", value):
        return ""
    if re.match(r"^(?:见|参见|另见|→)\s*[一-龯々ぁ-ゖァ-ヺー・\[\]・･（）()\s]+[。.]?$", value):
        return ""
    return value


def clean_meta_gloss_target(value: str) -> str:
    value = strip_parenthetical_headword_prefix(value)
    value = re.sub(r"[（(][^)）]*[)）]", "", value)
    return value.strip(" 　，,；;。.")


def strip_zhwiktionary_headword_usage_prefix(value: str) -> str:
    return re.sub(
        r"^[一-龯々ぁ-ゖァ-ヺー・]+【[^】]*(?:[ぁ-ゖァ-ヺー「」～]|常用|多用|接)[^】]*】\s*",
        "",
        value,
        count=1,
    ).strip()


def strip_leading_japanese_usage_bracket(value: str) -> str:
    return re.sub(
        r"^【[^】]*(?:[一-龯々ぁ-ゖァ-ヺー「」～]|常用|多用|接)[^】]*】\s*",
        "",
        value,
        count=1,
    ).strip()


def strip_latin_usage_bracket(value: str) -> str:
    return re.sub(
        r"^【[A-Za-z0-9 ._-]+】\s*",
        "",
        value,
        count=1,
    ).strip()


def strip_zhwiktionary_semantic_prefix(value: str) -> str:
    return re.sub(
        r"^〔[^〕]+〕\s*",
        "",
        value,
        count=1,
    ).strip()


def strip_numbered_gloss_prefix(value: str) -> str:
    return re.sub(r"^\d+[.．、]\s*", "", value, count=1).strip()


def strip_trailing_japanese_variant_note(value: str) -> str:
    return re.sub(r"[，,、]\s*【[^】]+】.*$", "", value, count=1).strip()


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


def contains_latin(value: str) -> bool:
    return bool(re.search(r"[A-Za-z]", value))


def is_japanese_example_line(value: str) -> bool:
    if not contains_kana(value):
        return False
    if re.search(r"(的|义|语|词|谦|称|表示|用于|源于|简称|缩写|读作|形式|被动|否定|敬语|多用|常用)", value):
        return False
    return True


def starts_with_japanese_example(value: str) -> bool:
    first_chunk = re.split(r"\s+", value.strip(), maxsplit=1)[0]
    return is_japanese_example_line(first_chunk)


def is_likely_example_translation(value: str) -> bool:
    return not contains_kana(value)


def is_useless_zhwiktionary_gloss_part(value: str) -> bool:
    if not value:
        return True
    if value in {"自サ", "他サ", "自他サ", "他五", "自五", "他下一", "自下一", "补动五"}:
        return True
    if contains_kana(value) and re.fullmatch(r"[一-龯々ぁ-ゖァ-ヺー・]+", value):
        return True
    if contains_kana(value) and re.search(r"[をにでがはへとて][一-龯々ぁ-ゖァ-ヺー]", value):
        return True
    return bool(re.fullmatch(r"=+.*=+", value))


def simplify_zh_gloss(value: str) -> str:
    return opencc_t2s().convert(value).replace("芸术", "艺术")


@lru_cache(maxsize=1)
def opencc_t2s() -> OpenCC:
    return OpenCC("t2s")


def extract_gloss_readings(value: str) -> tuple[str, ...]:
    value = normalize_gloss_source(value)
    match = re.match(r"^[（(]([ぁ-んァ-ンー・\s0-9０-９⓪①②③④⑤⑥⑦⑧⑨/／;；]+)[）)]", value)
    if not match:
        return ()
    return split_readings(match.group(1))


def extract_gloss_parts_of_speech(value: str) -> tuple[str, ...]:
    _, parts_of_speech = split_clean_gloss(value)
    return parts_of_speech


def readings_match(reading: str, expected_readings: tuple[str, ...]) -> bool:
    normalized = set(split_readings(reading))
    expected = {
        form
        for value in expected_readings
        for form in reading_match_forms(katakana_to_hiragana(value))
    }
    return bool(normalized & expected)


def reading_match_forms(value: str) -> tuple[str, ...]:
    if value.endswith("する") and len(value) > 2:
        return (value, value.removesuffix("する"))
    return (value,)


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
    cleaned, _ = split_clean_gloss(value)
    return cleaned


def split_clean_gloss(value: str) -> tuple[str, tuple[str, ...]]:
    value = normalize_gloss_source(value)
    value = strip_leading_gloss_parenthetical(value)
    labels: list[str] = []
    value = strip_leading_gloss_numbers(value)
    while True:
        match = re.match(r"^【([^】]+)】\s*", value)
        if not match:
            break
        labels.extend(normalize_zh_dict_pos_label(match.group(1)))
        value = value[match.end():].lstrip()
        value = strip_leading_gloss_numbers(value)
    value, text_labels = strip_text_pos_prefix(value)
    labels.extend(text_labels)
    return value.strip(), tuple(unique_strings(labels))


def strip_leading_gloss_numbers(value: str) -> str:
    return re.sub(r"^(?:[0-9０-９]+[.．、]?|[⓪①②③④⑤⑥⑦⑧⑨])\s*", "", value, count=1).strip()


def strip_leading_gloss_parenthetical(value: str) -> str:
    return re.sub(r"^[（(][^）)]{1,40}[）)]\s*", "", value, count=1).strip()


def strip_text_pos_prefix(value: str) -> tuple[str, list[str]]:
    for raw in sorted(ZH_DICT_POS_LABELS, key=len, reverse=True):
        match = re.match(rf"^{re.escape(raw)}(?:\s+|　+)", value)
        if not match:
            continue
        return value[match.end():].strip(), normalize_zh_dict_pos_label(raw)
    return value, []


def normalize_zh_dict_pos_label(value: str) -> list[str]:
    raw = re.sub(r"\s+", "", str(value or ""))
    raw = raw.strip("[]【】")
    if not raw:
        return []
    label = ZH_DICT_POS_LABELS.get(raw)
    if label:
        return [label]
    labels: list[str] = []
    for item in re.split(r"[·・/／,，;；、]+", raw):
        label = ZH_DICT_POS_LABELS.get(item)
        if label:
            labels.append(label)
    return unique_strings(labels)
