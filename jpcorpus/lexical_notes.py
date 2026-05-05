from __future__ import annotations

import gzip
import re
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Iterable, Iterator
from xml.etree import ElementTree as ET

import httpx

from .paths import DEFAULT_JMDICT, DEFAULT_KANJIDIC2, ensure_parent


JMDICT_URL = "http://ftp.edrdg.org/pub/Nihongo/JMdict_e.gz"
KANJIDIC2_URL = "http://ftp.edrdg.org/pub/Nihongo/kanjidic2.xml.gz"

MAX_JMDICT_ENTRIES_PER_WORD = 1
MAX_FORMS_PER_WORD = 4
MAX_TAGS_PER_WORD = 4
MAX_KANJI_PER_WORD = 8
MAX_SENSES_PER_WORD = 3
MAX_GLOSSES_PER_SENSE = 3
MAX_DICTIONARY_EXAMPLES_PER_WORD = 2

HIDDEN_FORM_TAGS = {
    "rarely used kanji form",
    "search-only kanji form",
}

SENSE_TAG_LABELS = {
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
    "vulgar expression or word": "粗俗语",
    "dated term": "旧语",
}


POS_LABELS = {
    "noun (common) (futsuumeishi)": "名词",
    "noun, used as a suffix": "名词・接尾",
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
    "Ichidan verb - kureru special class": "一段・くれる",
    "Godan verb - Iku/Yuku special class": "五段・行く",
    "Godan verb with 'u' ending": "五段・う",
    "Godan verb with `u' ending": "五段・う",
    "Godan verb with 'ku' ending": "五段・く",
    "Godan verb with `ku' ending": "五段・く",
    "Godan verb with 'gu' ending": "五段・ぐ",
    "Godan verb with `gu' ending": "五段・ぐ",
    "Godan verb with 'su' ending": "五段・す",
    "Godan verb with `su' ending": "五段・す",
    "Godan verb with 'tsu' ending": "五段・つ",
    "Godan verb with `tsu' ending": "五段・つ",
    "Godan verb with 'nu' ending": "五段・ぬ",
    "Godan verb with `nu' ending": "五段・ぬ",
    "Godan verb with 'bu' ending": "五段・ぶ",
    "Godan verb with `bu' ending": "五段・ぶ",
    "Godan verb with 'mu' ending": "五段・む",
    "Godan verb with `mu' ending": "五段・む",
    "Godan verb with 'ru' ending": "五段・る",
    "Godan verb with `ru' ending": "五段・る",
    "Kuru verb - special class": "カ变",
    "Suru verb - included": "サ变",
    "Suru verb - special class": "サ变",
    "transitive verb": "他动",
    "intransitive verb": "自动",
    "n": "名词",
    "pn": "代词",
    "adv": "副词",
    "adj-i": "い形容词",
    "adj-na": "な形容词",
    "v1": "一段动词",
    "v5u": "五段・う",
    "v5k": "五段・く",
    "v5g": "五段・ぐ",
    "v5s": "五段・す",
    "v5t": "五段・つ",
    "v5n": "五段・ぬ",
    "v5b": "五段・ぶ",
    "v5m": "五段・む",
    "v5r": "五段・る",
    "vt": "他动",
    "vi": "自动",
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
    senses: tuple["JMDictSense", ...] = ()


@dataclass(frozen=True)
class JMDictExample:
    japanese: str
    text: str | None = None
    translations: tuple[tuple[str, str], ...] = ()
    source_id: str | None = None
    source_type: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {"japanese": self.japanese}
        if self.text:
            payload["text"] = self.text
        if self.translations:
            payload["translations"] = {
                lang: text for lang, text in self.translations if lang and text
            }
        if self.source_id or self.source_type:
            payload["source"] = {
                key: value
                for key, value in {
                    "id": self.source_id,
                    "type": self.source_type,
                }.items()
                if value
            }
        return payload


@dataclass(frozen=True)
class JMDictSense:
    glosses: tuple[str, ...]
    parts_of_speech: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    examples: tuple[JMDictExample, ...] = ()

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {"glosses": list(self.glosses)}
        if self.parts_of_speech:
            payload["parts_of_speech"] = list(self.parts_of_speech)
        if self.tags:
            payload["tags"] = list(self.tags)
        if self.examples:
            payload["examples"] = [example.to_dict() for example in self.examples]
        return payload


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

    def notes_for(
        self,
        surface: str,
        reading: str | None = None,
        *,
        meaning_hint: str | None = None,
    ) -> dict[str, object] | None:
        jmdict_entries = self._jmdict_entries(surface, reading, meaning_hint=meaning_hint)
        kanji_notes = [
            note
            for char in surface
            if (note := self.kanji_by_literal.get(char)) is not None
        ][:MAX_KANJI_PER_WORD]
        if not jmdict_entries and not kanji_notes:
            return None

        payload: dict[str, object] = {}
        if jmdict_entries:
            spellings = visible_forms(
                unique_forms(form for entry in jmdict_entries for form in entry.spellings),
                preferred_text=surface,
            )
            readings = visible_forms(
                unique_forms(form for entry in jmdict_entries for form in entry.readings),
                preferred_text=reading,
            )
            parts_of_speech = compact_pos_labels(
                label_pos(pos) for entry in jmdict_entries for pos in entry.parts_of_speech
            )
            if spellings:
                payload["spellings"] = [form.to_dict() for form in spellings[:MAX_FORMS_PER_WORD]]
            if readings:
                payload["readings"] = [form.to_dict() for form in readings[:MAX_FORMS_PER_WORD]]
            if parts_of_speech:
                payload["parts_of_speech"] = parts_of_speech[:MAX_TAGS_PER_WORD]
            senses = unique_senses(
                sense for entry in jmdict_entries for sense in entry.senses
            )
            if senses:
                payload["senses"] = [
                    sense.to_dict()
                    for sense in senses[:MAX_SENSES_PER_WORD]
                ]
            examples = unique_examples(
                example for sense in senses for example in sense.examples
            )
            if examples:
                payload["dictionary_examples"] = [
                    example.to_dict()
                    for example in examples[:MAX_DICTIONARY_EXAMPLES_PER_WORD]
                ]
        if kanji_notes:
            payload["kanji"] = [note.to_dict() for note in kanji_notes]
        return payload

    def _jmdict_entries(
        self,
        surface: str,
        reading: str | None,
        *,
        meaning_hint: str | None,
    ) -> list[JMDictEntry]:
        seen: set[tuple[tuple[str, ...], tuple[str, ...]]] = set()
        entries = self._dedupe_jmdict_entries(
            sorted_jmdict_candidates(
                self.jmdict_by_key.get(surface, []),
                surface,
                reading,
                meaning_hint,
            ),
            seen,
        )
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
    senses = tuple(jmdict_sense_from_xml(sense) for sense in element.findall("sense"))
    return JMDictEntry(
        spellings=spellings,
        readings=readings,
        parts_of_speech=tuple(parts_of_speech),
        senses=tuple(sense for sense in senses if sense.glosses),
    )


def jmdict_sense_from_xml(element: ET.Element) -> JMDictSense:
    glosses = tuple(child_texts(element, "gloss")[:MAX_GLOSSES_PER_SENSE])
    parts_of_speech = tuple(
        compact_pos_labels(label_pos(text) for text in child_texts(element, "pos"))
    )
    tags = tuple(
        unique_strings(
            label
            for tag_name in ("misc", "field", "dial")
            for tag in child_texts(element, tag_name)
            if (label := label_sense_tag(tag))
        )
    )
    examples = tuple(
        example
        for example_element in element.findall("example")
        if (example := jmdict_example_from_xml(example_element)) is not None
    )
    return JMDictSense(
        glosses=glosses,
        parts_of_speech=parts_of_speech,
        tags=tags,
        examples=examples,
    )


def jmdict_example_from_xml(element: ET.Element) -> JMDictExample | None:
    japanese = None
    translations: list[tuple[str, str]] = []
    for sentence in element.findall("ex_sent"):
        text = (sentence.text or "").strip()
        if not text:
            continue
        lang = xml_lang(sentence)
        if lang == "jpn":
            japanese = text
        elif lang:
            translations.append((lang, text))
    if not japanese:
        return None
    source = element.find("ex_srce")
    return JMDictExample(
        japanese=japanese,
        text=child_text(element, "ex_text"),
        translations=tuple(translations),
        source_id=(source.text.strip() if source is not None and source.text else None),
        source_type=source.attrib.get("exsrc_type") if source is not None else None,
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


def xml_lang(element: ET.Element) -> str:
    return (
        element.attrib.get("{http://www.w3.org/XML/1998/namespace}lang")
        or element.attrib.get("xml:lang")
        or element.attrib.get("lang")
        or ""
    ).strip()


def unique_forms(forms: Iterable[JMDictForm]) -> list[JMDictForm]:
    seen: set[str] = set()
    results: list[JMDictForm] = []
    for form in forms:
        if not form.text or form.text in seen:
            continue
        seen.add(form.text)
        results.append(form)
    return results


def visible_forms(forms: list[JMDictForm], *, preferred_text: str | None) -> list[JMDictForm]:
    visible: list[JMDictForm] = []
    preferred = preferred_text or ""
    for form in forms:
        if form.text == preferred:
            visible.append(clean_form_tags(form))
            break
    for form in forms:
        if form.text == preferred or has_hidden_form_tag(form):
            continue
        if form.common:
            visible.append(clean_form_tags(form))
    for form in forms:
        if form.text == preferred or has_hidden_form_tag(form):
            continue
        if not form.common and not form.tags:
            visible.append(clean_form_tags(form))
    return unique_forms(visible)


def clean_form_tags(form: JMDictForm) -> JMDictForm:
    return JMDictForm(
        text=form.text,
        tags=tuple(tag for tag in form.tags if tag not in HIDDEN_FORM_TAGS),
        common=form.common,
    )


def has_hidden_form_tag(form: JMDictForm) -> bool:
    return any(tag in HIDDEN_FORM_TAGS for tag in form.tags)


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


def unique_senses(values: Iterable[JMDictSense]) -> list[JMDictSense]:
    seen: set[tuple[str, ...]] = set()
    results: list[JMDictSense] = []
    for sense in values:
        if not sense.glosses or sense.glosses in seen:
            continue
        seen.add(sense.glosses)
        results.append(sense)
    return results


def unique_examples(values: Iterable[JMDictExample]) -> list[JMDictExample]:
    seen: set[tuple[str, tuple[tuple[str, str], ...]]] = set()
    results: list[JMDictExample] = []
    for example in values:
        identity = (example.japanese, example.translations)
        if not example.japanese or identity in seen:
            continue
        seen.add(identity)
        results.append(example)
    return results


def sorted_jmdict_candidates(
    candidates: Iterable[JMDictEntry],
    surface: str,
    reading: str | None,
    meaning_hint: str | None,
) -> list[JMDictEntry]:
    reading_keys = split_reading_keys(reading)
    hint_tokens = meaning_tokens(meaning_hint)
    return sorted(
        candidates,
        key=lambda entry: (
            -jmdict_meaning_score(entry, hint_tokens),
            jmdict_surface_rank(entry, surface),
            not jmdict_entry_matches_reading(entry, reading_keys),
            not any(form.common for form in entry.spellings),
            not any(form.common for form in entry.readings),
        ),
    )


def jmdict_meaning_score(entry: JMDictEntry, hint_tokens: set[str]) -> int:
    if not hint_tokens:
        return 0
    gloss_tokens = {
        token
        for sense in entry.senses
        for gloss in sense.glosses
        for token in meaning_tokens(gloss)
    }
    return len(hint_tokens & gloss_tokens)


def jmdict_surface_rank(entry: JMDictEntry, surface: str) -> int:
    if any(form.text == surface for form in entry.spellings):
        return 0
    if not entry.spellings:
        return 1
    if is_kana_text(surface):
        return 2
    return 1


def jmdict_entry_matches_reading(entry: JMDictEntry, reading_keys: set[str]) -> bool:
    if not reading_keys:
        return True
    return any(form.text in reading_keys for form in entry.readings)


def split_reading_keys(reading: str | None) -> set[str]:
    if not reading:
        return set()
    return {
        part.strip()
        for part in reading.replace("；", ";").replace("、", ";").replace(",", ";").split(";")
        if part.strip()
    }


def is_kana_text(value: str) -> bool:
    return bool(value) and all(
        "\u3040" <= char <= "\u30ff" or char in {"ー", "・"}
        for char in value
    )


def meaning_tokens(value: str | None) -> set[str]:
    if not value:
        return set()
    stop_words = {
        "a",
        "an",
        "and",
        "for",
        "in",
        "of",
        "one",
        "or",
        "the",
        "to",
        "with",
    }
    return {
        token
        for token in re.findall(r"[a-z]+", value.casefold())
        if len(token) > 1 and token not in stop_words
    }


def compact_pos_labels(values: Iterable[str]) -> list[str]:
    labels = unique_strings(values)
    if len(labels) > 1:
        labels = [
            label
            for label in labels
            if label not in {"助动词", "辅助形容词"}
        ]
    return labels


def label_pos(value: str) -> str:
    return POS_LABELS.get(value, value)


def label_sense_tag(value: str) -> str:
    return SENSE_TAG_LABELS.get(value, "")


@contextmanager
def open_maybe_gzip(path: Path) -> Iterator[BinaryIO]:
    if path.suffix == ".gz":
        with gzip.open(path, "rb") as handle:
            yield handle
    else:
        with path.open("rb") as handle:
            yield handle
