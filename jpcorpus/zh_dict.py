from __future__ import annotations

import json
import gzip
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import httpx

from .paths import DEFAULT_ZH_DICT, DEFAULT_ZHWIKTIONARY_JA_DICT, DEFAULT_ZHWIKTIONARY_RAW, ensure_parent


DEFAULT_ZH_DICT_URL = (
    "https://raw.githubusercontent.com/lxl66566/"
    "Japanese-Chinese-thesaurus/main/final.json"
)
ZHWIKTIONARY_RAW_URL = "https://kaikki.org/zhwiktionary/raw-wiktextract-data.jsonl.gz"
ZHWIKTIONARY_FORM_SKIP_TAGS = {"romanization", "past", "continuative", "archaic"}
TRADITIONAL_GLOSS_CHARS = str.maketrans(
    {
        "與": "与",
        "專": "专",
        "業": "业",
        "叢": "丛",
        "喪": "丧",
        "嚴": "严",
        "國": "国",
        "圓": "圆",
        "圖": "图",
        "場": "场",
        "聲": "声",
        "學": "学",
        "實": "实",
        "對": "对",
        "屬": "属",
        "島": "岛",
        "帶": "带",
        "幫": "帮",
        "廣": "广",
        "廢": "废",
        "後": "后",
        "從": "从",
        "動": "动",
        "復": "复",
        "愛": "爱",
        "應": "应",
        "戀": "恋",
        "戰": "战",
        "戶": "户",
        "拋": "抛",
        "據": "据",
        "數": "数",
        "斷": "断",
        "於": "于",
        "時": "时",
        "會": "会",
        "條": "条",
        "樣": "样",
        "標": "标",
        "樂": "乐",
        "權": "权",
        "氣": "气",
        "漢": "汉",
        "為": "为",
        "無": "无",
        "狀": "状",
        "獸": "兽",
        "現": "现",
        "產": "产",
        "畫": "画",
        "發": "发",
        "盜": "盗",
        "確": "确",
        "禮": "礼",
        "稱": "称",
        "種": "种",
        "穩": "稳",
        "簡": "简",
        "類": "类",
        "紅": "红",
        "級": "级",
        "經": "经",
        "繼": "继",
        "續": "续",
        "聲": "声",
        "聽": "听",
        "與": "与",
        "舊": "旧",
        "處": "处",
        "號": "号",
        "蟲": "虫",
        "補": "补",
        "見": "见",
        "親": "亲",
        "覺": "觉",
        "覽": "览",
        "讀": "读",
        "變": "变",
        "讓": "让",
        "詞": "词",
        "試": "试",
        "該": "该",
        "話": "话",
        "語": "语",
        "說": "说",
        "調": "调",
        "論": "论",
        "證": "证",
        "譯": "译",
        "豐": "丰",
        "貓": "猫",
        "貿": "贸",
        "資": "资",
        "賣": "卖",
        "質": "质",
        "起": "起",
        "車": "车",
        "轉": "转",
        "進": "进",
        "過": "过",
        "選": "选",
        "還": "还",
        "醫": "医",
        "關": "关",
        "開": "开",
        "間": "间",
        "題": "题",
        "顯": "显",
        "風": "风",
        "馬": "马",
        "體": "体",
        "高": "高",
        "鳴": "鸣",
        "鳥": "鸟",
    }
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
    readings: dict[str, tuple[str, ...]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path = DEFAULT_ZH_DICT) -> "ChineseGlossary":
        paths = [path]
        if path == DEFAULT_ZH_DICT and DEFAULT_ZHWIKTIONARY_JA_DICT.exists():
            paths.append(DEFAULT_ZHWIKTIONARY_JA_DICT)
        entries: dict[str, str] = {}
        readings: dict[str, tuple[str, ...]] = {}
        for glossary_path in paths:
            loaded_entries, loaded_readings = load_glossary_payload(glossary_path)
            entries.update(loaded_entries)
            for key in loaded_entries:
                entry_readings = loaded_readings.get(key)
                if entry_readings:
                    readings[key] = entry_readings
                else:
                    readings.pop(key, None)
        entries.update(CHINESE_GLOSS_OVERRIDES)
        for key in CHINESE_GLOSS_OVERRIDES:
            readings.pop(key, None)
        return cls(entries, readings)

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


def load_glossary_payload(path: Path) -> tuple[dict[str, str], dict[str, tuple[str, ...]]]:
    if not path.exists():
        return {}, {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Chinese glossary must be a JSON object: {path}")
    entries: dict[str, str] = {}
    readings: dict[str, tuple[str, ...]] = {}
    for key, value in payload.items():
        key_text = str(key)
        if isinstance(value, dict):
            value_text = str(value.get("gloss") or "")
            entry_readings = tuple(str(item) for item in value.get("readings") or [] if str(item))
        else:
            value_text = str(value)
            entry_readings = extract_gloss_readings(value_text)
        entries[key_text] = clean_gloss(value_text)
        if entry_readings:
            readings[key_text] = entry_readings
    return entries, readings


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
        key: {"gloss": value["gloss"], "readings": value.get("readings") or []}
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
    return {
        "gloss": "；".join(sense_glosses[:5]),
        "readings": readings,
        "score": zhwiktionary_entry_score(item, readings),
    }


def zhwiktionary_sense_glosses(item: dict[str, Any]) -> list[str]:
    primary: list[str] = []
    secondary: list[str] = []
    for sense in item.get("senses") or []:
        if not isinstance(sense, dict) or "no-gloss" in (sense.get("tags") or []):
            continue
        glosses = [
            simplify_zh_gloss(normalize_gloss_source(str(value)))
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


def simplify_zh_gloss(value: str) -> str:
    return value.translate(TRADITIONAL_GLOSS_CHARS)


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
