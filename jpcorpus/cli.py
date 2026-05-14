from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

from .env import load_dotenv
from .paths import ensure_parent
from .viewer import serve_viewer


load_dotenv()

DEFAULT_VIEWER_CORPUS = Path("corpus.json")
DEFAULT_VIEWER_HOST = "127.0.0.1"
DEFAULT_VIEWER_PORT = 8767
HELP_TEXT = """Usage: jpcorpus [OPTIONS]

Open the local jpcorpus app.

Options:
  -h, --help  Show this message and exit.
"""


def main(argv: list[str] | None = None) -> None:
    """Open the local viewer."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in {"-h", "--help"}:
        typer.echo(HELP_TEXT.rstrip())
        return
    if args:
        typer.echo(f"Unknown argument: {args[0]}", err=True)
        typer.echo("Usage: jpcorpus [OPTIONS]", err=True)
        raise SystemExit(2)
    launch_viewer(
        DEFAULT_VIEWER_CORPUS,
        host=DEFAULT_VIEWER_HOST,
        port=DEFAULT_VIEWER_PORT,
        open_browser=True,
    )


def ensure_viewer_corpus(corpus: Path) -> None:
    if corpus.exists():
        return
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
    typer.echo(f"Created starter corpus: {corpus}")


def launch_viewer(corpus: Path, *, host: str, port: int, open_browser: bool) -> None:
    ensure_viewer_corpus(corpus)
    serve_viewer(corpus, host=host, port=port, open_browser=open_browser, echo=typer.echo)
