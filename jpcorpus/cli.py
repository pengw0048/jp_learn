from __future__ import annotations

import os
from pathlib import Path

import typer

from .analysis import analyze_paths, analyze_subtitles
from .anime_db import AnimeOfflineIndex, download_latest_anime_db
from .anki_export import export_anki_deck
from .bangumi import BangumiClient, collection_to_show, run_oauth_flow
from .corpus_export import write_corpus_json
from .env import load_dotenv
from .jimaku import JimakuClient
from .jlpt import download_jlpt_words, load_jlpt_words, write_sample_jlpt
from .i18n import SUPPORTED_LANGUAGES
from .paths import (
    DEFAULT_ANIME_DB,
    DEFAULT_JIMAKU_CACHE,
    DEFAULT_JLPT_WORDS,
    DEFAULT_STATE_DB,
    DEFAULT_ZH_DICT,
    ensure_dir,
    ensure_parent,
)
from .report import build_markdown_report
from .state import State
from .viewer import serve_viewer
from .zh_dict import ChineseGlossary, download_zh_dict


load_dotenv()

app = typer.Typer(help="Build a personal JLPT corpus from watched Japanese media.")
link_app = typer.Typer(help="Link external accounts.")
export_app = typer.Typer(help="Export study artifacts.")
data_app = typer.Typer(help="Manage local cache files.")
app.add_typer(link_app, name="link")
app.add_typer(export_app, name="export")
app.add_typer(data_app, name="data")


def user_agent() -> str:
    return os.environ.get("JPCORPUS_USER_AGENT", "peng/jpcorpus-v0.1")


def validate_language(language: str) -> str:
    if language not in SUPPORTED_LANGUAGES:
        raise typer.BadParameter(
            f"Unsupported language '{language}'. Choose one of: {', '.join(SUPPORTED_LANGUAGES)}."
        )
    return language


def load_analysis(
    *,
    state_db: Path,
    jlpt_words: Path,
    subtitles: list[Path] | None,
    max_examples_per_word: int = 3,
    context_lines: int = 2,
):
    words = load_jlpt_words(jlpt_words)
    if subtitles:
        return analyze_paths(
            paths=subtitles,
            jlpt_words=words,
            max_examples_per_word=max_examples_per_word,
            context_lines=context_lines,
        )
    state = State(state_db)
    return analyze_subtitles(
        watched_show_count=state.count_watched_shows(),
        subtitle_files=state.list_subtitle_files(),
        jlpt_words=words,
        max_examples_per_word=max_examples_per_word,
        context_lines=context_lines,
    )


@link_app.command("bangumi")
def link_bangumi(
    client_id: str = typer.Option(
        None,
        envvar="JPCORPUS_BANGUMI_CLIENT_ID",
        help="Bangumi OAuth client ID.",
    ),
    client_secret: str = typer.Option(
        None,
        envvar="JPCORPUS_BANGUMI_CLIENT_SECRET",
        help="Bangumi OAuth client secret.",
    ),
    redirect_uri: str = typer.Option(
        os.environ.get("JPCORPUS_BANGUMI_REDIRECT_URI", "http://127.0.0.1:8080/callback"),
        help="Redirect URI registered in the Bangumi app.",
    ),
    state_db: Path = typer.Option(DEFAULT_STATE_DB, help="SQLite state database."),
    open_browser: bool = typer.Option(True, help="Open the authorization URL in a browser."),
) -> None:
    """Link Bangumi with OAuth authorization-code flow."""
    if not client_id or not client_secret:
        raise typer.BadParameter(
            "Set JPCORPUS_BANGUMI_CLIENT_ID and JPCORPUS_BANGUMI_CLIENT_SECRET."
        )
    result = run_oauth_flow(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        user_agent=user_agent(),
        open_browser=open_browser,
    )
    client = BangumiClient(access_token=result.token["access_token"], user_agent=user_agent())
    me = client.me()
    State(state_db).save_token(
        "bangumi",
        result.token,
        user_id=me.get("id") or result.token.get("user_id"),
        username=me.get("username"),
        expires_at=result.expires_at,
    )
    typer.echo(f"Linked Bangumi user: {me.get('username') or me.get('nickname') or me.get('id')}")


@app.command()
def sync(
    state_db: Path = typer.Option(DEFAULT_STATE_DB, help="SQLite state database."),
    anime_db: Path = typer.Option(DEFAULT_ANIME_DB, help="Anime Offline Database JSON path."),
    cache_dir: Path = typer.Option(DEFAULT_JIMAKU_CACHE, help="Jimaku subtitle cache directory."),
    max_shows: int | None = typer.Option(None, help="Limit watched shows during development."),
    max_files_per_show: int = typer.Option(24, help="Maximum subtitle files to download per show."),
    download_subtitles: bool = typer.Option(True, help="Download Jimaku subtitles after sync."),
) -> None:
    """Sync Bangumi watched anime, map IDs, and cache matching Jimaku subtitles."""
    state = State(state_db)
    token = state.get_token("bangumi")
    if token is None:
        raise typer.BadParameter("Bangumi is not linked. Run `jpcorpus link bangumi` first.")
    client = BangumiClient(access_token=token["access_token"], user_agent=user_agent())
    username = token.get("username")
    if not username:
        me = client.me()
        username = me["username"]

    typer.echo("Syncing Bangumi watched anime...")
    collections = client.watched_collections(username, max_items=max_shows)
    for item in collections:
        state.save_watched_show(collection_to_show(item))
    typer.echo(f"Saved {len(collections)} watched anime from Bangumi.")

    index: AnimeOfflineIndex | None = None
    if anime_db.exists():
        typer.echo("Mapping titles through Anime Offline Database...")
        index = AnimeOfflineIndex.load(anime_db)
        mapped = 0
        for show in state.list_watched_shows(limit=max_shows):
            record = index.match_show(show)
            if record:
                mapped += 1
                state.update_external_ids(
                    show.bangumi_id,
                    mal_id=record.ids.mal_id,
                    anilist_id=record.ids.anilist_id,
                    anidb_id=record.ids.anidb_id,
                )
        typer.echo(f"Mapped {mapped} watched anime to external IDs.")
    else:
        typer.echo(f"Anime database missing at {anime_db}; subtitle search will use titles only.")

    if not download_subtitles:
        return

    api_key = os.environ.get("JIMAKU_API_KEY")
    if not api_key:
        typer.echo("JIMAKU_API_KEY is not set; skipping subtitle download.")
        return

    ensure_dir(cache_dir)
    jimaku = JimakuClient(api_key=api_key, user_agent=user_agent())
    downloaded = 0
    matched = 0
    for show in state.list_watched_shows(limit=max_shows):
        title = show.title_jp or show.display_title
        try:
            subtitles = jimaku.download_for_show(
                title=title,
                anilist_id=show.anilist_id,
                cache_dir=cache_dir,
                max_files=max_files_per_show,
            )
        except Exception as exc:
            typer.echo(f"Jimaku miss for {show.display_title}: {exc}")
            continue
        if subtitles:
            matched += 1
        for subtitle in subtitles:
            downloaded += 1
            state.update_external_ids(show.bangumi_id, jimaku_entry_id=subtitle.entry.id)
            state.save_subtitle_file(
                bangumi_id=show.bangumi_id,
                jimaku_entry_id=subtitle.entry.id,
                episode=subtitle.episode,
                name=subtitle.file.name,
                url=subtitle.file.url,
                size=subtitle.file.size,
                local_path=subtitle.path,
            )
    typer.echo(f"Jimaku matched {matched} shows and cached {downloaded} subtitle files.")


@app.command()
def report(
    output: Path = typer.Option(Path("report.md"), help="Markdown report output path."),
    state_db: Path = typer.Option(DEFAULT_STATE_DB, help="SQLite state database."),
    jlpt_words: Path = typer.Option(DEFAULT_JLPT_WORDS, help="JLPT word list JSON/CSV path."),
    level: int = typer.Option(3, min=1, max=5, help="Primary JLPT level to rank."),
    language: str = typer.Option(
        "zh",
        "--language",
        "-l",
        help=f"Report language: {', '.join(SUPPORTED_LANGUAGES)}.",
    ),
    top: int = typer.Option(50, help="Words to include in the target-level table."),
    examples_per_word: int = typer.Option(2, min=1, help="Examples to show per target word."),
    context_lines: int = typer.Option(2, min=0, help="Subtitle lines to keep before and after each example."),
    subtitles: list[Path] | None = typer.Option(
        None,
        help="Analyze local subtitle files instead of the synced state database.",
    ),
    zh_dict: Path = typer.Option(DEFAULT_ZH_DICT, help="Japanese-Chinese glossary JSON path."),
) -> None:
    """Generate a Markdown personal frequency report."""
    language = validate_language(language)
    analysis = load_analysis(
        state_db=state_db,
        jlpt_words=jlpt_words,
        subtitles=subtitles,
        max_examples_per_word=examples_per_word,
        context_lines=context_lines,
    )
    ensure_parent(output)
    output.write_text(
        build_markdown_report(
            analysis,
            target_level=level,
            top=top,
            language=language,
            examples_per_word=examples_per_word,
            zh_glossary=ChineseGlossary.load(zh_dict) if language == "zh" else None,
        ),
        encoding="utf-8",
    )
    typer.echo(f"Wrote report: {output}")


@export_app.command("anki")
def export_anki(
    output: Path = typer.Option(Path("personal-jlpt.apkg"), help="Anki .apkg output path."),
    state_db: Path = typer.Option(DEFAULT_STATE_DB, help="SQLite state database."),
    jlpt_words: Path = typer.Option(DEFAULT_JLPT_WORDS, help="JLPT word list JSON/CSV path."),
    level: int | None = typer.Option(None, min=1, max=5, help="Only export one JLPT level."),
    limit: int = typer.Option(200, help="Maximum cards to export."),
    deck_name: str = typer.Option("Personal JLPT Corpus", help="Anki deck name."),
    subtitles: list[Path] | None = typer.Option(
        None,
        help="Analyze local subtitle files instead of the synced state database.",
    ),
) -> None:
    """Export a genanki .apkg deck from cached subtitles."""
    analysis = load_analysis(state_db=state_db, jlpt_words=jlpt_words, subtitles=subtitles)
    export_anki_deck(
        analysis,
        output=output,
        level=level,
        limit=limit,
        deck_name=deck_name,
    )
    typer.echo(f"Wrote Anki deck: {output}")


@export_app.command("corpus-json")
def export_corpus_json(
    output: Path = typer.Option(Path("corpus.json"), help="Structured corpus JSON output path."),
    state_db: Path = typer.Option(DEFAULT_STATE_DB, help="SQLite state database."),
    jlpt_words: Path = typer.Option(DEFAULT_JLPT_WORDS, help="JLPT word list JSON/CSV path."),
    level: int | None = typer.Option(None, min=1, max=5, help="Only export one JLPT level."),
    limit: int | None = typer.Option(None, help="Maximum words to export."),
    examples_per_word: int = typer.Option(3, min=1, help="Examples to include per word."),
    context_lines: int = typer.Option(2, min=0, help="Subtitle lines to keep before and after each example."),
    zh_dict: Path = typer.Option(DEFAULT_ZH_DICT, help="Japanese-Chinese glossary JSON path."),
    subtitles: list[Path] | None = typer.Option(
        None,
        help="Analyze local subtitle files instead of the synced state database.",
    ),
) -> None:
    """Export structured word/source/example data for future UI work."""
    analysis = load_analysis(
        state_db=state_db,
        jlpt_words=jlpt_words,
        subtitles=subtitles,
        max_examples_per_word=examples_per_word,
        context_lines=context_lines,
    )
    write_corpus_json(
        analysis,
        output,
        level=level,
        limit=limit,
        examples_per_word=examples_per_word,
        zh_glossary=ChineseGlossary.load(zh_dict),
    )
    typer.echo(f"Wrote corpus JSON: {output}")


@app.command()
def view(
    corpus: Path = typer.Option(Path("corpus.json"), help="Structured corpus JSON file."),
    host: str = typer.Option("127.0.0.1", help="Host to bind."),
    port: int = typer.Option(8765, min=0, max=65535, help="Port to bind. Use 0 for a random port."),
    open_browser: bool = typer.Option(True, help="Open the viewer in a browser."),
) -> None:
    """Serve the local corpus web viewer."""
    serve_viewer(corpus, host=host, port=port, open_browser=open_browser, echo=typer.echo)


@data_app.command("fetch-anime-db")
def fetch_anime_db(
    output: Path = typer.Option(DEFAULT_ANIME_DB, help="Output JSON path."),
) -> None:
    """Download the latest Anime Offline Database JSON release asset."""
    path = download_latest_anime_db(output)
    typer.echo(f"Downloaded Anime Offline Database: {path}")


@data_app.command("init-sample-jlpt")
def init_sample_jlpt(
    output: Path = typer.Option(DEFAULT_JLPT_WORDS, help="Output JSON path."),
    overwrite: bool = typer.Option(False, help="Overwrite an existing file."),
) -> None:
    """Create a tiny sample JLPT list so the pipeline can run end to end."""
    if output.exists() and not overwrite:
        typer.echo(f"Already exists: {output}")
        return
    write_sample_jlpt(output)
    typer.echo(f"Wrote sample JLPT list: {output}")


@data_app.command("fetch-jlpt-words")
def fetch_jlpt_words(
    output: Path = typer.Option(DEFAULT_JLPT_WORDS, help="Output JSON path."),
    source_url: str = typer.Option(
        "https://raw.githubusercontent.com/elzup/jlpt-word-list/master/out/all.csv",
        help="CSV word list source URL.",
    ),
) -> None:
    """Download and normalize a community JLPT vocabulary list."""
    path = download_jlpt_words(output, source_url=source_url)
    words = load_jlpt_words(path)
    counts = ", ".join(f"N{level}: {words.total_by_level(level)}" for level in range(5, 0, -1))
    typer.echo(f"Wrote JLPT word list: {path} ({counts})")


@data_app.command("fetch-zh-dict")
def fetch_zh_dict(
    output: Path = typer.Option(DEFAULT_ZH_DICT, help="Output JSON path."),
    source_url: str = typer.Option(
        "https://raw.githubusercontent.com/lxl66566/Japanese-Chinese-thesaurus/main/final.json",
        help="Japanese-Chinese glossary source URL.",
    ),
) -> None:
    """Download a lightweight Japanese-Chinese glossary for Chinese reports."""
    path = download_zh_dict(output, source_url=source_url)
    glossary = ChineseGlossary.load(path)
    typer.echo(f"Wrote Japanese-Chinese glossary: {path} ({len(glossary.entries)} entries)")
