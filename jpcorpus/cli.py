from __future__ import annotations

import json
import sys
from pathlib import Path

from .env import load_dotenv
from .paths import ensure_parent
from .viewer import serve_viewer


load_dotenv()

DEFAULT_VIEWER_CORPUS = Path("corpus.json")
DEFAULT_VIEWER_HOST = "127.0.0.1"
DEFAULT_VIEWER_PORT = 8767
FIRST_RUN_HINT = (
    "Next: open Maintenance, fill the required keys, then run Full refresh. "
    "After that, use Refresh for normal updates."
)
HELP_TEXT = """Usage: jpcorpus [OPTIONS]

Open the local jpcorpus app.

Options:
  -h, --help  Show this message and exit.
"""


def main(argv: list[str] | None = None) -> None:
    """Open the local viewer."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in {"-h", "--help"}:
        echo(HELP_TEXT.rstrip())
        return
    if args:
        echo(f"Unknown argument: {args[0]}", err=True)
        echo("Usage: jpcorpus [OPTIONS]", err=True)
        raise SystemExit(2)
    launch_viewer(
        DEFAULT_VIEWER_CORPUS,
        host=DEFAULT_VIEWER_HOST,
        port=DEFAULT_VIEWER_PORT,
        open_browser=True,
    )


def ensure_viewer_corpus(corpus: Path) -> bool:
    if corpus.exists():
        return False
    if corpus.name != "corpus.json":
        raise FileNotFoundError(f"Corpus JSON does not exist: {corpus}")
    payload = {
        "schema_version": 13,
        "generated_at": None,
        "summary": {
            "show_count": 0,
            "subtitle_file_count": 0,
            "lyric_file_count": 0,
            "text_file_count": 0,
            "total_tokens": 0,
            "unique_tokens": 0,
        },
        "shows": [],
        "words": [],
        "sources": [],
    }
    ensure_parent(corpus)
    corpus.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    echo(f"Created starter corpus: {corpus}")
    return True


def is_empty_viewer_corpus(corpus: Path) -> bool:
    try:
        payload = json.loads(corpus.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    words = payload.get("words")
    sources = payload.get("sources")
    summary = payload.get("summary") or {}
    return (
        isinstance(words, list)
        and isinstance(sources, list)
        and not words
        and not sources
        and not any(
            summary.get(key, 0)
            for key in (
                "show_count",
                "subtitle_file_count",
                "lyric_file_count",
                "text_file_count",
                "total_tokens",
                "unique_tokens",
            )
        )
    )


def launch_viewer(corpus: Path, *, host: str, port: int, open_browser: bool) -> None:
    created = ensure_viewer_corpus(corpus)
    if created or is_empty_viewer_corpus(corpus):
        echo(FIRST_RUN_HINT)
    serve_viewer(corpus, host=host, port=port, open_browser=open_browser, echo=echo)


def echo(message: str = "", *, err: bool = False) -> None:
    print(message, file=sys.stderr if err else sys.stdout)
