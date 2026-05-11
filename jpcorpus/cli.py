from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import typer

from .analysis import analyze_media
from .anime_db import AnimeOfflineIndex, download_latest_anime_db
from .anki_export import export_anki_deck
from .bangumi import SUBJECT_MUSIC, BangumiClient, collection_to_music_tracks, collection_to_show, run_oauth_flow
from .corpus_export import write_corpus_json
from .env import load_dotenv
from .jimaku import JimakuClient
from .jlpt import download_jlpt_words, load_jlpt_words, write_sample_jlpt
from .lexical_notes import download_jmdict, download_kanjidic2
from .i18n import SUPPORTED_LANGUAGES
from .llm import (
    DEFAULT_ANTHROPIC_BASE_URL,
    DEFAULT_ANTHROPIC_MODEL,
    AnthropicClient,
    AppleFoundationModelsClient,
    LLMConfig,
    OpenAICompatibleClient,
    apply_cached_annotations_file,
    annotate_corpus_file,
)
from .models import SubtitleFile
from .lyrics import (
    LRCLIB_ALBUM_CACHE_PURPOSE,
    LRCLIB_ALBUM_CACHE_VERSION,
    LRCLIB_CACHE_PURPOSE,
    LRCLIB_CACHE_VERSION,
    LrcLibClient,
    is_probably_instrumental_title,
    lyric_album_artists,
    lyric_album_cache_key,
    lyric_album_search_params,
    lyric_cache_key,
    write_lrclib_lyric,
)
from .paths import (
    DEFAULT_ANIME_DB,
    DEFAULT_JMDICT,
    DEFAULT_JIMAKU_CACHE,
    DEFAULT_JLPT_WORDS,
    DEFAULT_KANJIDIC2,
    DEFAULT_LYRICS_CACHE,
    DEFAULT_STATE_DB,
    DEFAULT_TEXTS_DIR,
    DEFAULT_ZH_DICT,
    ensure_dir,
    ensure_parent,
)
from .report import build_markdown_report
from .state import State
from .texts import discover_text_files, text_file_from_path
from .viewer import serve_viewer
from .zh_dict import ChineseGlossary, download_zh_dict


load_dotenv()

app = typer.Typer(help="Build a personal JLPT corpus from watched Japanese media.")
link_app = typer.Typer(help="Link external accounts.")
export_app = typer.Typer(help="Export study artifacts.")
data_app = typer.Typer(help="Manage local cache files.")
lyrics_app = typer.Typer(help="Sync music tracks and cache lyric files.")
app.add_typer(link_app, name="link")
app.add_typer(export_app, name="export")
app.add_typer(data_app, name="data")
app.add_typer(lyrics_app, name="lyrics")


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
    texts: list[Path] | None = None,
    text_dir: Path = DEFAULT_TEXTS_DIR,
    max_examples_per_word: int = 3,
    context_lines: int = 2,
    context_min_chars: int = 0,
    context_max_lines: int | None = None,
):
    words = load_jlpt_words(jlpt_words)
    text_files = (
        [text_file_from_path(path) for path in texts]
        if texts
        else discover_text_files(text_dir)
    )
    if subtitles:
        return analyze_media(
            watched_show_count=1,
            music_track_count=0,
            subtitle_files=[
                SubtitleFile(
                    bangumi_id=index + 1,
                    show_title="Local subtitles",
                    path=path,
                    name=path.name,
                )
                for index, path in enumerate(subtitles)
            ],
            lyric_files=[],
            text_files=text_files,
            jlpt_words=words,
            max_examples_per_word=max_examples_per_word,
            context_lines=context_lines,
            context_min_chars=context_min_chars,
            context_max_lines=context_max_lines,
        )
    state = State(state_db)
    return analyze_media(
        watched_show_count=state.count_watched_shows(),
        music_track_count=state.count_music_tracks(),
        subtitle_files=state.list_subtitle_files(),
        lyric_files=state.list_lyric_files(),
        text_files=text_files,
        jlpt_words=words,
        max_examples_per_word=max_examples_per_word,
        context_lines=context_lines,
        context_min_chars=context_min_chars,
        context_max_lines=context_max_lines,
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
    character_shows = 0
    character_count = 0
    for show in state.list_watched_shows(limit=max_shows):
        try:
            characters = client.subject_characters(show.bangumi_id)
        except Exception as exc:
            typer.echo(f"Bangumi character miss for {show.display_title}: {exc}")
            continue
        state.save_show_characters(show.bangumi_id, characters)
        character_shows += 1
        character_count += len(characters)
    typer.echo(f"Saved {character_count} Bangumi character names for {character_shows} shows.")

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


@lyrics_app.command("sync")
def sync_lyrics(
    state_db: Path = typer.Option(DEFAULT_STATE_DB, help="SQLite state database."),
    max_albums: int | None = typer.Option(None, help="Limit Bangumi music collections during development."),
    max_tracks: int | None = typer.Option(None, help="Limit saved tracks during development."),
) -> None:
    """Sync listened Bangumi music collections and split albums into tracks."""
    state = State(state_db)
    token = state.get_token("bangumi")
    if token is None:
        raise typer.BadParameter("Bangumi is not linked. Run `jpcorpus link bangumi` first.")
    client = BangumiClient(access_token=token["access_token"], user_agent=user_agent())
    username = token.get("username")
    if not username:
        me = client.me()
        username = me["username"]

    typer.echo("Syncing Bangumi music collections...")
    collections = client.watched_collections(
        username,
        subject_type=SUBJECT_MUSIC,
        max_items=max_albums,
    )
    saved_tracks = 0
    for item in collections:
        subject = item.get("subject") or {}
        subject_id = item.get("subject_id") or subject.get("id")
        if subject_id is None:
            continue
        try:
            full_subject = client.subject(int(subject_id))
            item = {**item, "subject": full_subject}
            subject = full_subject
        except Exception as exc:
            typer.echo(f"Bangumi subject miss for {subject.get('name') or subject_id}: {exc}")
        try:
            episodes = client.episodes(int(subject_id))
        except Exception as exc:
            typer.echo(f"Bangumi track miss for {subject.get('name') or subject_id}: {exc}")
            episodes = []
        for track in collection_to_music_tracks(item, episodes):
            if max_tracks is not None and saved_tracks >= max_tracks:
                break
            state.save_music_track(track)
            saved_tracks += 1
        if max_tracks is not None and saved_tracks >= max_tracks:
            break
    typer.echo(f"Saved {saved_tracks} tracks from {len(collections)} Bangumi music collections.")


@lyrics_app.command("fetch")
def fetch_lyrics(
    state_db: Path = typer.Option(DEFAULT_STATE_DB, help="SQLite state database."),
    cache_dir: Path = typer.Option(DEFAULT_LYRICS_CACHE, help="LRCLIB lyric cache directory."),
    limit: int | None = typer.Option(None, help="Maximum tracks to try this run."),
    overwrite: bool = typer.Option(False, help="Rewrite cached lyric files from the versioned cache."),
    force: bool = typer.Option(False, "--force", help="Ignore versioned cache entries and query LRCLIB again."),
    concurrency: int = typer.Option(4, min=1, max=16, help="Parallel LRCLIB requests."),
) -> None:
    """Fetch cached lyrics from LRCLIB for synced Bangumi music tracks."""
    state = State(state_db)
    tracks = state.list_music_tracks()
    if not tracks:
        typer.echo("No Bangumi music tracks yet. Run `jpcorpus lyrics sync` first.")
        return

    cached = {
        lyric_file.track_key
        for lyric_file in state.list_lyric_files()
        if lyric_file.provider == "lrclib"
    }
    cached_paths = {
        lyric_file.track_key: lyric_file.path
        for lyric_file in state.list_lyric_files()
        if lyric_file.provider == "lrclib"
    }
    ua = user_agent()
    attempted = 0
    matched = 0
    cache_hits = 0
    skipped_cached = 0
    skipped_missed = 0
    skipped_instrumental = 0
    pending = []
    for track in tracks:
        if limit is not None and attempted >= limit:
            break
        if not overwrite and track.track_key in cached:
            skipped_cached += 1
            continue
        cache_key = lyric_cache_key(track)
        if not force:
            cache_entry = state.get_cache_entry(
                purpose=LRCLIB_CACHE_PURPOSE,
                cache_key=cache_key,
                version=LRCLIB_CACHE_VERSION,
            )
            if cache_entry and cache_entry["status"] == "hit":
                result = cache_entry["value"]
                lyric_file = write_lrclib_lyric(track, result, cache_dir=cache_dir)
                state.save_lyric_file(lyric_file, raw_payload=result)
                stale_path = cached_paths.get(track.track_key)
                if stale_path and stale_path != lyric_file.path:
                    stale_path.unlink(missing_ok=True)
                cache_hits += 1
                matched += 1
                continue
            if cache_entry and cache_entry["status"] == "miss":
                value = cache_entry["value"]
                reason = str(value.get("reason") or "not_found")
                if overwrite:
                    remove_cached_lyric(state, cached_paths, track.track_key)
                state.save_lyric_miss(
                    track_key=track.track_key,
                    provider="lrclib",
                    reason=reason,
                    detail=value.get("detail"),
                )
                skipped_missed += 1
                continue
        if is_probably_instrumental_title(track.title):
            if overwrite:
                remove_cached_lyric(state, cached_paths, track.track_key)
            state.save_cache_entry(
                purpose=LRCLIB_CACHE_PURPOSE,
                cache_key=cache_key,
                version=LRCLIB_CACHE_VERSION,
                status="miss",
                value={"reason": "instrumental", "detail": track.title},
            )
            state.save_lyric_miss(
                track_key=track.track_key,
                provider="lrclib",
                reason="instrumental",
                detail=track.title,
            )
            skipped_instrumental += 1
            typer.echo(f"Skipping instrumental track: {track.title}")
            continue
        attempted += 1
        pending.append((track, cache_key))

    album_results = load_lrclib_album_candidates(
        state=state,
        tracks=[track for track, _cache_key in pending],
        user_agent_value=ua,
        force=force,
        concurrency=concurrency,
    )

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {
            executor.submit(
                fetch_lrclib_track,
                track,
                ua,
                album_results.get(track.album_title, []),
            ): (track, cache_key)
            for track, cache_key in pending
        }
        for future in as_completed(futures):
            track, cache_key = futures[future]
            result, error = future.result()
            if error:
                state.save_lyric_miss(
                    track_key=track.track_key,
                    provider="lrclib",
                    reason="error",
                    detail=error,
                )
                typer.echo(f"LRCLIB miss for {track.title}: {error}")
                continue
            if result is None:
                if overwrite:
                    remove_cached_lyric(state, cached_paths, track.track_key)
                state.save_cache_entry(
                    purpose=LRCLIB_CACHE_PURPOSE,
                    cache_key=cache_key,
                    version=LRCLIB_CACHE_VERSION,
                    status="miss",
                    value={"reason": "not_found"},
                )
                state.save_lyric_miss(
                    track_key=track.track_key,
                    provider="lrclib",
                    reason="not_found",
                )
                typer.echo(f"LRCLIB miss for {track.title}")
                continue
            state.save_cache_entry(
                purpose=LRCLIB_CACHE_PURPOSE,
                cache_key=cache_key,
                version=LRCLIB_CACHE_VERSION,
                status="hit",
                value=result,
            )
            lyric_file = write_lrclib_lyric(track, result, cache_dir=cache_dir)
            state.save_lyric_file(lyric_file, raw_payload=result)
            stale_path = cached_paths.get(track.track_key)
            if stale_path and stale_path != lyric_file.path:
                stale_path.unlink(missing_ok=True)
            matched += 1
            typer.echo(f"Cached lyrics: {track.title}")
    typer.echo(
        "LRCLIB matched "
        f"{matched} tracks "
        f"({attempted} queried, "
        f"{skipped_cached} cached, {cache_hits} cache hits, "
        f"{skipped_missed} cached misses, "
        f"{skipped_instrumental} instrumental skipped)."
    )


def load_lrclib_album_candidates(
    *,
    state: State,
    tracks: list[Any],
    user_agent_value: str,
    force: bool,
    concurrency: int,
) -> dict[str, list[dict[str, Any]]]:
    album_tracks: dict[str, list[Any]] = {}
    for track in tracks:
        album_tracks.setdefault(track.album_title, []).append(track)

    results: dict[str, list[dict[str, Any]]] = {}
    pending = []
    for album_title, tracks_for_album in album_tracks.items():
        artists = lyric_album_artists(tracks_for_album)
        cache_key = lyric_album_cache_key(album_title, artists)
        if not force:
            cache_entry = state.get_cache_entry(
                purpose=LRCLIB_ALBUM_CACHE_PURPOSE,
                cache_key=cache_key,
                version=LRCLIB_ALBUM_CACHE_VERSION,
            )
            if cache_entry and cache_entry["status"] == "hit":
                value = cache_entry["value"]
                results[album_title] = value if isinstance(value, list) else []
                continue
            if cache_entry and cache_entry["status"] == "miss":
                results[album_title] = []
                continue
        pending.append((album_title, artists, cache_key))

    if pending:
        typer.echo(f"Searching LRCLIB album candidates for {len(pending)} albums...")

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {
            executor.submit(fetch_lrclib_album, album_title, artists, user_agent_value): (
                album_title,
                cache_key,
            )
            for album_title, artists, cache_key in pending
        }
        for future in as_completed(futures):
            album_title, cache_key = futures[future]
            album_results, error = future.result()
            if error:
                typer.echo(f"LRCLIB album search miss for {album_title}: {error}")
                results[album_title] = []
                continue
            if album_results:
                state.save_cache_entry(
                    purpose=LRCLIB_ALBUM_CACHE_PURPOSE,
                    cache_key=cache_key,
                    version=LRCLIB_ALBUM_CACHE_VERSION,
                    status="hit",
                    value=album_results,
                )
                typer.echo(f"Cached LRCLIB album candidates: {album_title} ({len(album_results)})")
            else:
                state.save_cache_entry(
                    purpose=LRCLIB_ALBUM_CACHE_PURPOSE,
                    cache_key=cache_key,
                    version=LRCLIB_ALBUM_CACHE_VERSION,
                    status="miss",
                    value={"reason": "not_found"},
                )
            results[album_title] = album_results
    return results


def fetch_lrclib_album(
    album_title: str,
    artists: list[str],
    user_agent_value: str,
) -> tuple[list[dict[str, Any]], str | None]:
    client = LrcLibClient(user_agent=user_agent_value)
    candidates: dict[str, dict[str, Any]] = {}
    try:
        for params in lyric_album_search_params(album_title, artists):
            for result in client.search(**params):
                source_id = str(result.get("id") or result.get("trackId") or repr(result))
                candidates[source_id] = result
    except Exception as exc:
        return [], str(exc)
    return list(candidates.values()), None


def fetch_lrclib_track(
    track,
    user_agent_value: str,
    extra_results: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    client = LrcLibClient(user_agent=user_agent_value)
    try:
        return client.best_match(track, extra_results=extra_results), None
    except Exception as exc:
        return None, str(exc)


def remove_cached_lyric(state: State, cached_paths: dict[str, Path], track_key: str) -> None:
    state.delete_lyric_file(track_key=track_key, provider="lrclib")
    path = cached_paths.get(track_key)
    if path:
        path.unlink(missing_ok=True)


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
    context_lines: int = typer.Option(2, min=0, help="Source blocks to keep before and after each example."),
    subtitles: list[Path] | None = typer.Option(
        None,
        help="Analyze local subtitle files instead of the synced state database.",
    ),
    texts: list[Path] | None = typer.Option(
        None,
        "--text",
        "--texts",
        help="Import local Japanese .txt or .epub files as text/book sources.",
    ),
    text_dir: Path = typer.Option(
        DEFAULT_TEXTS_DIR,
        help="Directory of .txt and .epub files to import when --text is omitted.",
    ),
    zh_dict: Path = typer.Option(DEFAULT_ZH_DICT, help="Japanese-Chinese glossary JSON path."),
) -> None:
    """Generate a Markdown personal frequency report."""
    language = validate_language(language)
    analysis = load_analysis(
        state_db=state_db,
        jlpt_words=jlpt_words,
        subtitles=subtitles,
        texts=texts,
        text_dir=text_dir,
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
    texts: list[Path] | None = typer.Option(
        None,
        "--text",
        "--texts",
        help="Import local Japanese .txt or .epub files as text/book sources.",
    ),
    text_dir: Path = typer.Option(
        DEFAULT_TEXTS_DIR,
        help="Directory of .txt and .epub files to import when --text is omitted.",
    ),
) -> None:
    """Export a genanki .apkg deck from cached media."""
    analysis = load_analysis(
        state_db=state_db,
        jlpt_words=jlpt_words,
        subtitles=subtitles,
        texts=texts,
        text_dir=text_dir,
    )
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
    examples_per_word: int = typer.Option(5, min=1, help="Examples to include per word."),
    context_lines: int = typer.Option(2, min=0, help="Source blocks to keep before and after each example."),
    context_min_chars: int = typer.Option(
        40,
        min=0,
        help="Keep collecting nearby source blocks until each side has at least this many characters.",
    ),
    context_max_lines: int = typer.Option(
        4,
        min=1,
        help="Maximum nearby source blocks to keep on each side.",
    ),
    zh_dict: Path = typer.Option(DEFAULT_ZH_DICT, help="Japanese-Chinese glossary JSON path."),
    jmdict: Path = typer.Option(DEFAULT_JMDICT, help="JMdict/JMdict_e_examp path for offline lexical notes."),
    kanjidic2: Path = typer.Option(DEFAULT_KANJIDIC2, help="KANJIDIC2 XML/GZ path for offline kanji notes."),
    lexical_notes: bool = typer.Option(
        True,
        "--lexical-notes/--no-lexical-notes",
        help="Include compact notes from local JMdict and KANJIDIC2 files when available.",
    ),
    subtitles: list[Path] | None = typer.Option(
        None,
        help="Analyze local subtitle files instead of the synced state database.",
    ),
    texts: list[Path] | None = typer.Option(
        None,
        "--text",
        "--texts",
        help="Import local Japanese .txt or .epub files as text/book sources.",
    ),
    text_dir: Path = typer.Option(
        DEFAULT_TEXTS_DIR,
        help="Directory of .txt and .epub files to import when --text is omitted.",
    ),
) -> None:
    """Export structured word/source/example data for future UI work."""
    analysis = load_analysis(
        state_db=state_db,
        jlpt_words=jlpt_words,
        subtitles=subtitles,
        texts=texts,
        text_dir=text_dir,
        max_examples_per_word=max(examples_per_word * 12, 24),
        context_lines=context_lines,
        context_min_chars=context_min_chars,
        context_max_lines=context_max_lines,
    )
    write_corpus_json(
        analysis,
        output,
        level=level,
        limit=limit,
        examples_per_word=examples_per_word,
        zh_glossary=ChineseGlossary.load(zh_dict),
        jmdict_path=jmdict if lexical_notes else None,
        kanjidic2_path=kanjidic2 if lexical_notes else None,
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


@app.command()
def annotate(
    input: Path = typer.Option(Path("corpus.json"), help="Input corpus JSON path."),
    output: Path = typer.Option(Path("corpus.annotated.json"), help="Annotated corpus JSON output path."),
    state_db: Path = typer.Option(DEFAULT_STATE_DB, help="SQLite state database for annotation cache."),
    model: str | None = typer.Option(
        None,
        help="LLM model name for the configured provider.",
    ),
    provider: str = typer.Option(
        "openai-compatible",
        envvar="JPCORPUS_LLM_PROVIDER",
        help="LLM provider: openai-compatible, anthropic, or apple.",
    ),
    base_url: str = typer.Option(
        "https://api.openai.com/v1",
        envvar="JPCORPUS_LLM_BASE_URL",
        help="OpenAI-compatible API base URL.",
    ),
    anthropic_base_url: str = typer.Option(
        DEFAULT_ANTHROPIC_BASE_URL,
        envvar="ANTHROPIC_BASE_URL",
        help="Anthropic Messages API base URL.",
    ),
    api_key: str | None = typer.Option(
        None,
        help="API key override. Local OpenAI-compatible servers may not require one.",
    ),
    limit: int = typer.Option(20, min=1, help="Maximum examples to annotate this run."),
    concurrency: int = typer.Option(1, min=1, max=16, help="Parallel LLM annotation requests."),
    rpm: float | None = typer.Option(
        None,
        min=0.1,
        help="Maximum uncached LLM requests per minute. Cache hits do not count.",
    ),
    overwrite: bool = typer.Option(False, help="Regenerate existing annotations."),
    cache_only: bool = typer.Option(
        False,
        "--cache-only",
        help="Only apply existing cached annotations; do not call an LLM.",
    ),
    use_show_context: bool = typer.Option(
        False,
        "--use-show-context",
        help="Include cached Bangumi show summaries in the LLM prompt for names and references.",
    ),
) -> None:
    """Annotate corpus examples with translation and usage notes."""
    if provider == "apple":
        resolved_model = "apple"
        resolved_base_url = ""
        client = None if cache_only else AppleFoundationModelsClient(use_show_context=use_show_context)
    elif provider == "anthropic":
        resolved_model = model or os.environ.get("ANTHROPIC_MODEL") or DEFAULT_ANTHROPIC_MODEL
        resolved_base_url = os.environ.get("JPCORPUS_ANTHROPIC_BASE_URL") or anthropic_base_url
        client = None
        if not cache_only:
            resolved_api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
            if not resolved_api_key:
                raise typer.BadParameter("Set ANTHROPIC_API_KEY or pass --api-key for Anthropic.")
            client = AnthropicClient(
                LLMConfig(
                    model=resolved_model,
                    base_url=resolved_base_url,
                    api_key=resolved_api_key,
                    use_show_context=use_show_context,
                )
            )
    elif provider == "openai-compatible":
        resolved_model = model or os.environ.get("JPCORPUS_LLM_MODEL")
        if not resolved_model:
            raise typer.BadParameter("Set --model or JPCORPUS_LLM_MODEL.")
        resolved_base_url = base_url
        client = None
        if not cache_only:
            if not api_key:
                api_key = os.environ.get("JPCORPUS_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
            if "api.openai.com" in base_url and not api_key:
                raise typer.BadParameter("Set JPCORPUS_LLM_API_KEY or OPENAI_API_KEY for OpenAI.")
            client = OpenAICompatibleClient(
                LLMConfig(
                    model=resolved_model,
                    base_url=base_url,
                    api_key=api_key,
                    use_show_context=use_show_context,
                )
            )
    else:
        raise typer.BadParameter("Unsupported provider. Use 'openai-compatible', 'anthropic', or 'apple'.")
    cache_context = {
        "provider": provider,
        "model": resolved_model,
        "base_url": resolved_base_url,
        "use_show_context": use_show_context,
    }
    if cache_only:
        count = apply_cached_annotations_file(
            input,
            output,
            cache_state=State(state_db),
            cache_context=cache_context,
            limit=limit,
            overwrite=overwrite,
        )
        typer.echo(f"Applied {count} cached annotations: {output}")
        return

    errors = []

    def on_annotation_error(word: dict[str, Any], example: dict[str, Any], exc: Exception) -> None:
        errors.append((word, example, exc))
        label = word.get("word") or example.get("matched_text") or example.get("sentence") or "example"
        typer.echo(f"Annotation failed for {label}: {exc}", err=True)

    request_interval_seconds = 60.0 / rpm if rpm else 0.0
    count = 0
    try:
        count = annotate_corpus_file(
            input,
            output,
            client=client,
            limit=limit,
            overwrite=overwrite,
            cache_state=State(state_db),
            cache_context=cache_context,
            concurrency=concurrency,
            request_interval_seconds=request_interval_seconds,
            on_error=on_annotation_error,
        )
    finally:
        close_client = getattr(client, "close", None)
        if callable(close_client):
            close_client()
    if errors:
        typer.echo(f"Annotated {count} examples with {len(errors)} failures: {output}")
    else:
        typer.echo(f"Annotated {count} examples: {output}")


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


@data_app.command("fetch-jmdict")
def fetch_jmdict(
    output: Path = typer.Option(DEFAULT_JMDICT, help="Output JMdict_e_examp.gz-compatible path."),
    source_url: str = typer.Option(
        "http://ftp.edrdg.org/pub/Nihongo/JMdict_e_examp.gz",
        help="JMdict source URL.",
    ),
) -> None:
    """Download JMdict with examples for offline word-form and usage notes."""
    path = download_jmdict(output, source_url=source_url)
    typer.echo(f"Downloaded JMdict: {path}")


@data_app.command("fetch-kanjidic2")
def fetch_kanjidic2(
    output: Path = typer.Option(DEFAULT_KANJIDIC2, help="Output KANJIDIC2 XML/GZ path."),
    source_url: str = typer.Option(
        "http://ftp.edrdg.org/pub/Nihongo/kanjidic2.xml.gz",
        help="KANJIDIC2 source URL.",
    ),
) -> None:
    """Download KANJIDIC2 for offline kanji notes."""
    path = download_kanjidic2(output, source_url=source_url)
    typer.echo(f"Downloaded KANJIDIC2: {path}")


@data_app.command("fetch-lexical-resources")
def fetch_lexical_resources(
    jmdict_output: Path = typer.Option(DEFAULT_JMDICT, help="Output JMdict_e_examp.gz-compatible path."),
    kanjidic2_output: Path = typer.Option(DEFAULT_KANJIDIC2, help="Output KANJIDIC2 XML/GZ path."),
) -> None:
    """Download offline lexical resources used by the viewer."""
    jmdict_path = download_jmdict(jmdict_output)
    kanjidic2_path = download_kanjidic2(kanjidic2_output)
    typer.echo(f"Downloaded lexical resources: {jmdict_path}, {kanjidic2_path}")


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
