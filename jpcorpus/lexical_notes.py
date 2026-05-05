from __future__ import annotations

import gzip
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Iterable, Iterator
from xml.etree import ElementTree as ET

import httpx

from .paths import DEFAULT_JMDICT, DEFAULT_KANJIDIC2, ensure_parent


JMDICT_URL = "http://ftp.edrdg.org/pub/Nihongo/JMdict_e.gz"
KANJIDIC2_URL = "http://ftp.edrdg.org/pub/Nihongo/kanjidic2.xml.gz"

MAX_JMDICT_ENTRIES_PER_WORD = 2
MAX_FORMS_PER_WORD = 8
MAX_TAGS_PER_WORD = 10
MAX_KANJI_PER_WORD = 8


POS_LABELS = {
    "noun (common) (futsuumeishi)": "名词",
    "pronoun": "代词",
    "adverb (fukushi)": "副词",
    "adjective (keiyoushi)": "い形容词",
    "adjectival nouns or quasi-adjectives (keiyodoshi)": "な形容词",
    "adverbial noun (fukushitekimeishi)": "副词性名词",
    "auxiliary verb": "助动词",
    "auxiliary adjective": "辅助形容词",
    "conjunction": "接续词",
    "interjection (kandoushi)": "感叹词",
    "counter": "助数词",
    "particle": "助词",
    "prefix": "接头词",
    "suffix": "接尾词",
    "Ichidan verb": "一段动词",
    "Godan verb with 'u' ending": "五段动词・う",
    "Godan verb with `u' ending": "五段动词・う",
    "Godan verb with 'ku' ending": "五段动词・く",
    "Godan verb with `ku' ending": "五段动词・く",
    "Godan verb with 'gu' ending": "五段动词・ぐ",
    "Godan verb with `gu' ending": "五段动词・ぐ",
    "Godan verb with 'su' ending": "五段动词・す",
    "Godan verb with `su' ending": "五段动词・す",
    "Godan verb with 'tsu' ending": "五段动词・つ",
    "Godan verb with `tsu' ending": "五段动词・つ",
    "Godan verb with 'nu' ending": "五段动词・ぬ",
    "Godan verb with `nu' ending": "五段动词・ぬ",
    "Godan verb with 'bu' ending": "五段动词・ぶ",
    "Godan verb with `bu' ending": "五段动词・ぶ",
    "Godan verb with 'mu' ending": "五段动词・む",
    "Godan verb with `mu' ending": "五段动词・む",
    "Godan verb with 'ru' ending": "五段动词・る",
    "Godan verb with `ru' ending": "五段动词・る",
    "Kuru verb - special class": "カ变动词",
    "Suru verb - included": "サ变动词",
    "Suru verb - special class": "サ变动词",
    "transitive verb": "他动词",
    "intransitive verb": "自动词",
    "n": "名词",
    "pn": "代词",
    "adv": "副词",
    "adj-i": "い形容词",
    "adj-na": "な形容词",
    "v1": "一段动词",
    "v5u": "五段动词・う",
    "v5k": "五段动词・く",
    "v5g": "五段动词・ぐ",
    "v5s": "五段动词・す",
    "v5t": "五段动词・つ",
    "v5n": "五段动词・ぬ",
    "v5b": "五段动词・ぶ",
    "v5m": "五段动词・む",
    "v5r": "五段动词・る",
    "vt": "他动词",
    "vi": "自动词",
}

TAG_LABELS = {
    "word usually written using kana alone": "通常假名书写",
    "uk": "通常假名书写",
    "usually written using kana alone": "通常假名书写",
    "word containing irregular kanji usage": "汉字用法不规则",
    "word containing irregular kana usage": "假名用法不规则",
    "irregular okurigana usage": "送假名不规则",
    "ateji (phonetic) reading": "当字",
    "archaism": "古语",
    "obsolete term": "废语",
    "rare term": "少见",
    "slang": "俚语",
    "colloquialism": "口语",
    "honorific or respectful (sonkeigo) language": "尊敬语",
    "humble (kenjougo) language": "谦让语",
    "polite (teineigo) language": "礼貌语",
    "male term or language": "男性用语",
    "female term or language": "女性用语",
    "manga slang": "漫画用语",
    "children's language": "儿童语",
    "onomatopoeic or mimetic word": "拟声拟态",
    "sensitive": "敏感词",
    "vulgar expression or word": "粗俗语",
    "dated term": "旧语",
}


@dataclass(frozen=True)
class JMDictForm:
    text: str
    tags: tuple[str, ...] = ()
    common: bool = False

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {"text": self.text}
        if self.tags:
            payload["tags"] = list(self.tags)
        if self.common:
            payload["common"] = True
        return payload


@dataclass(frozen=True)
class JMDictEntry:
    spellings: tuple[JMDictForm, ...]
    readings: tuple[JMDictForm, ...]
    parts_of_speech: tuple[str, ...] = ()
    usage_tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class KanjiNote:
    literal: str
    meanings: tuple[str, ...] = ()
    on_readings: tuple[str, ...] = ()
    kun_readings: tuple[str, ...] = ()
    grade: str | None = None
    jlpt: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {"literal": self.literal}
        if self.meanings:
            payload["meanings"] = list(self.meanings)
        if self.on_readings:
            payload["on_readings"] = list(self.on_readings)
        if self.kun_readings:
            payload["kun_readings"] = list(self.kun_readings)
        if self.grade:
            payload["grade"] = self.grade
        if self.jlpt:
            payload["jlpt"] = self.jlpt
        return payload


class LexicalResourceIndex:
    def __init__(
        self,
        *,
        jmdict_by_key: dict[str, list[JMDictEntry]] | None = None,
        kanji_by_literal: dict[str, KanjiNote] | None = None,
    ) -> None:
        self.jmdict_by_key = jmdict_by_key or {}
        self.kanji_by_literal = kanji_by_literal or {}

    @classmethod
    def load_optional(
        cls,
        *,
        jmdict_path: Path | None = DEFAULT_JMDICT,
        kanjidic2_path: Path | None = DEFAULT_KANJIDIC2,
        target_keys: Iterable[str] = (),
        target_kanji: Iterable[str] = (),
    ) -> "LexicalResourceIndex":
        target_key_set = {key for key in target_keys if key}
        target_kanji_set = {char for char in target_kanji if char}
        jmdict = (
            parse_jmdict(jmdict_path, target_keys=target_key_set)
            if jmdict_path and jmdict_path.exists() and target_key_set
            else {}
        )
        kanji = (
            parse_kanjidic2(kanjidic2_path, target_kanji=target_kanji_set)
            if kanjidic2_path and kanjidic2_path.exists() and target_kanji_set
            else {}
        )
        return cls(jmdict_by_key=jmdict, kanji_by_literal=kanji)

    def notes_for(self, surface: str, reading: str | None = None) -> dict[str, object] | None:
        jmdict_entries = self._jmdict_entries(surface, reading)
        kanji_notes = [
            note
            for char in surface
            if (note := self.kanji_by_literal.get(char)) is not None
        ][:MAX_KANJI_PER_WORD]
        if not jmdict_entries and not kanji_notes:
            return None

        payload: dict[str, object] = {"sources": []}
        sources: list[str] = []
        if jmdict_entries:
            sources.append("JMdict")
            spellings = unique_forms(form for entry in jmdict_entries for form in entry.spellings)
            readings = unique_forms(form for entry in jmdict_entries for form in entry.readings)
            parts_of_speech = unique_strings(
                label_pos(pos) for entry in jmdict_entries for pos in entry.parts_of_speech
            )
            usage_tags = unique_strings(
                label_tag(tag) for entry in jmdict_entries for tag in entry.usage_tags
            )
            if spellings:
                payload["spellings"] = [form.to_dict() for form in spellings[:MAX_FORMS_PER_WORD]]
            if readings:
                payload["readings"] = [form.to_dict() for form in readings[:MAX_FORMS_PER_WORD]]
            if parts_of_speech:
                payload["parts_of_speech"] = parts_of_speech[:MAX_TAGS_PER_WORD]
            if usage_tags:
                payload["usage_tags"] = usage_tags[:MAX_TAGS_PER_WORD]
        if kanji_notes:
            sources.append("KANJIDIC2")
            payload["kanji"] = [note.to_dict() for note in kanji_notes]
        payload["sources"] = sources
        return payload

    def _jmdict_entries(self, surface: str, reading: str | None) -> list[JMDictEntry]:
        seen: set[tuple[tuple[str, ...], tuple[str, ...]]] = set()
        entries = self._dedupe_jmdict_entries(self.jmdict_by_key.get(surface, []), seen)
        if entries:
            return entries[:MAX_JMDICT_ENTRIES_PER_WORD]
        if reading:
            entries = self._dedupe_jmdict_entries(self.jmdict_by_key.get(reading, []), seen)
        return entries[:MAX_JMDICT_ENTRIES_PER_WORD]

    def _dedupe_jmdict_entries(
        self,
        candidates: Iterable[JMDictEntry],
        seen: set[tuple[tuple[str, ...], tuple[str, ...]]],
    ) -> list[JMDictEntry]:
        entries: list[JMDictEntry] = []
        for entry in candidates:
            identity = (
                tuple(form.text for form in entry.spellings),
                tuple(form.text for form in entry.readings),
            )
            if identity in seen:
                continue
            seen.add(identity)
            entries.append(entry)
            if len(entries) >= MAX_JMDICT_ENTRIES_PER_WORD:
                return entries
        return entries


def download_jmdict(
    path: Path = DEFAULT_JMDICT,
    *,
    source_url: str = JMDICT_URL,
    timeout: float = 120.0,
) -> Path:
    return download_binary_resource(path, source_url=source_url, timeout=timeout)


def download_kanjidic2(
    path: Path = DEFAULT_KANJIDIC2,
    *,
    source_url: str = KANJIDIC2_URL,
    timeout: float = 120.0,
) -> Path:
    return download_binary_resource(path, source_url=source_url, timeout=timeout)


def download_binary_resource(path: Path, *, source_url: str, timeout: float) -> Path:
    ensure_parent(path)
    temp_path = path.with_name(f".{path.name}.tmp")
    with httpx.stream("GET", source_url, timeout=timeout, follow_redirects=True) as response:
        response.raise_for_status()
        with temp_path.open("wb") as handle:
            for chunk in response.iter_bytes():
                handle.write(chunk)
    temp_path.replace(path)
    return path


def parse_jmdict(path: Path, *, target_keys: set[str]) -> dict[str, list[JMDictEntry]]:
    entries_by_key: dict[str, list[JMDictEntry]] = {}
    if not target_keys:
        return entries_by_key
    with open_maybe_gzip(path) as handle:
        for _event, element in ET.iterparse(handle, events=("end",)):
            if element.tag != "entry":
                continue
            entry = jmdict_entry_from_xml(element)
            keys = {form.text for form in entry.spellings} | {form.text for form in entry.readings}
            matched_keys = keys & target_keys
            if matched_keys:
                for key in matched_keys:
                    entries_by_key.setdefault(key, []).append(entry)
            element.clear()
    return entries_by_key


def parse_kanjidic2(path: Path, *, target_kanji: set[str]) -> dict[str, KanjiNote]:
    notes: dict[str, KanjiNote] = {}
    if not target_kanji:
        return notes
    with open_maybe_gzip(path) as handle:
        for _event, element in ET.iterparse(handle, events=("end",)):
            if element.tag != "character":
                continue
            literal = child_text(element, "literal")
            if literal in target_kanji:
                notes[literal] = kanji_note_from_xml(element)
            element.clear()
    return notes


def jmdict_entry_from_xml(element: ET.Element) -> JMDictEntry:
    spellings = tuple(
        JMDictForm(
            text=text,
            tags=tuple(child_texts(k_ele, "ke_inf")),
            common=bool(child_texts(k_ele, "ke_pri")),
        )
        for k_ele in element.findall("k_ele")
        if (text := child_text(k_ele, "keb"))
    )
    readings = tuple(
        JMDictForm(
            text=text,
            tags=tuple(child_texts(r_ele, "re_inf")),
            common=bool(child_texts(r_ele, "re_pri")),
        )
        for r_ele in element.findall("r_ele")
        if (text := child_text(r_ele, "reb"))
    )
    parts_of_speech = unique_strings(
        text
        for sense in element.findall("sense")
        for text in child_texts(sense, "pos")
    )
    usage_tags = unique_strings(
        text
        for sense in element.findall("sense")
        for tag_name in ("misc", "field", "dial", "s_inf")
        for text in child_texts(sense, tag_name)
    )
    return JMDictEntry(
        spellings=spellings,
        readings=readings,
        parts_of_speech=tuple(parts_of_speech),
        usage_tags=tuple(usage_tags),
    )


def kanji_note_from_xml(element: ET.Element) -> KanjiNote:
    literal = child_text(element, "literal") or ""
    meanings = unique_strings(
        meaning.text.strip()
        for meaning in element.findall("./reading_meaning/rmgroup/meaning")
        if meaning.text and not meaning.attrib.get("m_lang")
    )
    on_readings = unique_strings(
        reading.text.strip()
        for reading in element.findall("./reading_meaning/rmgroup/reading")
        if reading.text and reading.attrib.get("r_type") == "ja_on"
    )
    kun_readings = unique_strings(
        reading.text.strip()
        for reading in element.findall("./reading_meaning/rmgroup/reading")
        if reading.text and reading.attrib.get("r_type") == "ja_kun"
    )
    grade = child_text(element, "./misc/grade")
    jlpt = child_text(element, "./misc/jlpt")
    return KanjiNote(
        literal=literal,
        meanings=tuple(meanings[:4]),
        on_readings=tuple(on_readings[:6]),
        kun_readings=tuple(kun_readings[:6]),
        grade=grade,
        jlpt=jlpt,
    )


def target_keys_for_words(words: Iterable[object]) -> set[str]:
    keys: set[str] = set()
    for word in words:
        entry = getattr(word, "entry", None)
        surface = getattr(entry, "surface", None)
        reading = getattr(word, "display_reading", None)
        if surface:
            keys.add(str(surface))
        if reading:
            keys.add(str(reading))
    return keys


def target_kanji_for_words(words: Iterable[object]) -> set[str]:
    chars: set[str] = set()
    for word in words:
        entry = getattr(word, "entry", None)
        surface = str(getattr(entry, "surface", "") or "")
        chars.update(char for char in surface if is_cjk_kanji(char))
    return chars


def is_cjk_kanji(char: str) -> bool:
    return "\u4e00" <= char <= "\u9fff" or "\u3400" <= char <= "\u4dbf"


def child_text(element: ET.Element, path: str) -> str | None:
    child = element.find(path)
    if child is None or child.text is None:
        return None
    text = child.text.strip()
    return text or None


def child_texts(element: ET.Element, path: str) -> list[str]:
    return [
        child.text.strip()
        for child in element.findall(path)
        if child.text and child.text.strip()
    ]


def unique_forms(forms: Iterable[JMDictForm]) -> list[JMDictForm]:
    seen: set[str] = set()
    results: list[JMDictForm] = []
    for form in forms:
        if not form.text or form.text in seen:
            continue
        seen.add(form.text)
        results.append(form)
    return results


def unique_strings(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []
    for value in values:
        text = value.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        results.append(text)
    return results


def label_pos(value: str) -> str:
    return POS_LABELS.get(value, value)


def label_tag(value: str) -> str:
    return TAG_LABELS.get(value, value)


@contextmanager
def open_maybe_gzip(path: Path) -> Iterator[BinaryIO]:
    if path.suffix == ".gz":
        with gzip.open(path, "rb") as handle:
            yield handle
    else:
        with path.open("rb") as handle:
            yield handle
