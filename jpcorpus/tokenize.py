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
                Token(surface=surface, base=surface)
                for surface in FALLBACK_TOKEN_RE.findall(text)
            ]

        tokens: list[Token] = []
        for word in self._tagger(text):
            surface = word.surface.strip()
            if not surface or not FALLBACK_TOKEN_RE.search(surface):
                continue
            feature = word.feature
            pos = _get_feature(feature, "pos1")
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
            tokens.append(Token(surface=surface, base=base, reading=reading, pos=pos))
        return tokens


def _get_feature(feature: object, name: str) -> str | None:
    value = getattr(feature, name, None)
    if value in (None, "", "*"):
        return None
    return str(value)


def iter_tokens(texts: Iterable[str]) -> Iterable[Token]:
    tokenizer = JapaneseTokenizer()
    for text in texts:
        yield from tokenizer.tokenize(text)
