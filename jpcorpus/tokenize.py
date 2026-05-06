from __future__ import annotations

import re
from typing import Iterable

from .models import Token


FALLBACK_TOKEN_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff々〆ヵヶー]+")


class JapaneseTokenizer:
    def __init__(self) -> None:
        self._tagger = None
        try:
            import fugashi

            self._tagger = fugashi.Tagger()
        except Exception:
            self._tagger = None

    def tokenize(self, text: str) -> list[Token]:
        if self._tagger is None:
            return [
                Token(
                    surface=match.group(0),
                    base=match.group(0),
                    start=match.start(),
                    end=match.end(),
                )
                for match in FALLBACK_TOKEN_RE.finditer(text)
            ]

        tokens: list[Token] = []
        cursor = 0
        for word in self._tagger(text):
            raw_surface = word.surface
            start = text.find(raw_surface, cursor)
            if start < 0:
                start = text.find(raw_surface.strip(), cursor)
                raw_length = len(raw_surface.strip())
                leading_space = 0
            else:
                raw_length = len(raw_surface)
                leading_space = len(raw_surface) - len(raw_surface.lstrip())
            if start >= 0:
                cursor = max(cursor, start + raw_length)

            surface = raw_surface.strip()
            if not surface or not FALLBACK_TOKEN_RE.search(surface):
                continue
            feature = word.feature
            pos = _get_feature(feature, "pos1")
            pos_detail = _join_pos_detail(
                _get_feature(feature, "pos1"),
                _get_feature(feature, "pos2"),
                _get_feature(feature, "pos3"),
                _get_feature(feature, "pos4"),
            )
            if pos in {"補助記号", "空白", "記号"}:
                continue
            base = (
                _get_feature(feature, "orthBase")
                or _get_feature(feature, "lemma")
                or _get_feature(feature, "orth")
                or surface
            )
            reading = (
                _get_feature(feature, "kana")
                or _get_feature(feature, "kanaBase")
                or _get_feature(feature, "pron")
            )
            if base in {"*", ""}:
                base = surface
            token_start = start + leading_space if start >= 0 else None
            token_end = token_start + len(surface) if token_start is not None else None
            tokens.append(
                Token(
                    surface=surface,
                    base=base,
                    reading=reading,
                    pos=pos,
                    pos_detail=pos_detail,
                    start=token_start,
                    end=token_end,
                )
            )
        return tokens


def _get_feature(feature: object, name: str) -> str | None:
    value = getattr(feature, name, None)
    if value in (None, "", "*"):
        return None
    return str(value)


def _join_pos_detail(*values: str | None) -> str | None:
    parts = [value for value in values if value and value != "*"]
    return "-".join(parts) if parts else None


def iter_tokens(texts: Iterable[str]) -> Iterable[Token]:
    tokenizer = JapaneseTokenizer()
    for text in texts:
        yield from tokenizer.tokenize(text)
