from __future__ import annotations

import hashlib
from pathlib import Path

from .analysis import CorpusAnalysis, WordStats
from .paths import ensure_parent


MODEL_ID = 2_026_050_401
DECK_ID = 2_026_050_402


def export_anki_deck(
    analysis: CorpusAnalysis,
    *,
    output: Path,
    level: int | None = None,
    limit: int = 200,
    deck_name: str = "Personal JLPT Corpus",
) -> Path:
    try:
        import genanki
    except ImportError as exc:
        raise RuntimeError("Install genanki to export Anki decks.") from exc

    ensure_parent(output)
    model = genanki.Model(
        MODEL_ID,
        "Personal JLPT Word",
        fields=[
            {"name": "Word"},
            {"name": "Reading"},
            {"name": "Meaning"},
            {"name": "ExampleSentence"},
            {"name": "Source"},
        ],
        templates=[
            {
                "name": "Card 1",
                "qfmt": "<div class='word'>{{Word}}</div><div class='reading'>{{Reading}}</div>",
                "afmt": "{{FrontSide}}<hr><div>{{Meaning}}</div><p>{{ExampleSentence}}</p><p>{{Source}}</p>",
            }
        ],
        css="""
        .card { font-family: -apple-system, BlinkMacSystemFont, sans-serif; font-size: 20px; }
        .word { font-size: 42px; font-weight: 700; }
        .reading { color: #666; margin-top: 8px; }
        """,
    )
    deck = genanki.Deck(DECK_ID, deck_name)
    for stats in analysis.top_words(level=level, limit=limit):
        deck.add_note(_note_for_stats(genanki, model, stats))
    genanki.Package(deck).write_to_file(output)
    return output


def _note_for_stats(genanki: object, model: object, stats: WordStats) -> object:
    source = "、".join(name for name, _ in stats.sources.most_common(3))
    guid_source = f"{stats.entry.surface}|{stats.entry.reading}|{stats.entry.level}"
    guid = hashlib.sha1(guid_source.encode("utf-8")).hexdigest()
    return genanki.Note(
        model=model,
        guid=guid,
        fields=[
            stats.entry.surface,
            stats.entry.reading or "",
            stats.entry.meaning or "",
            stats.example_sentence or "",
            source,
        ],
    )

