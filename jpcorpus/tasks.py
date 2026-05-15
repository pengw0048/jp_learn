from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .analysis import analyze_media
from .anime_db import AnimeOfflineIndex, download_latest_anime_db
from .bangumi import SUBJECT_MUSIC, BangumiClient, collection_to_music_tracks, collection_to_show, run_oauth_flow
from .corpus_export import write_corpus_json
from .env import load_dotenv
from .jimaku import JimakuClient
from .jlpt import download_jlpt_words, load_jlpt_words, write_sample_jlpt
from .lexical_notes import download_jmdict
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
    DEFAULT_LYRICS_CACHE,
    DEFAULT_STATE_DB,
    DEFAULT_TEXTS_DIR,
    DEFAULT_ZH_DICT,
    DEFAULT_ZHWIKTIONARY_JA_DICT,
    DEFAULT_ZHWIKTIONARY_RAW,
    ensure_dir,
)
from .state import State
from .texts import discover_text_files, text_file_from_path
from .zh_dict import ChineseGlossary, download_zh_dict, download_zhwiktionary_ja_dict


load_dotenv()

def user_agent() -> str:
    return os.environ.get("JPCORPUS_USER_AGENT", "peng/jpcorpus-v0.1")


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


def link_bangumi(
    client_id: str | None = None,
    client_secret: str | None = None,
    redirect_uri: str = os.environ.get("JPCORPUS_BANGUMI_REDIRECT_URI", "http://127.0.0.1:8080/callback"),
    state_db: Path = DEFAULT_STATE_DB,
    open_browser: bool = True,
) -> None:
    """Link Bangumi with OAuth authorization-code flow."""
    if not client_id or not client_secret:
        raise ValueError(
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
    print(f"Linked Bangumi user: {me.get('username') or me.get('nickname') or me.get('id')}")


def sync(
    state_db: Path = DEFAULT_STATE_DB,
    anime_db: Path = DEFAULT_ANIME_DB,
    cache_dir: Path = DEFAULT_JIMAKU_CACHE,
    max_shows: int | None = None,
    max_files_per_show: int = 24,
    download_subtitles: bool = True,
) -> None:
    """Sync Bangumi watched anime, map IDs, and cache matching Jimaku subtitles."""
    state = State(state_db)
    token = state.get_token("bangumi")
    if token is None:
        raise ValueError("Bangumi is not linked. Save Bangumi credentials in the viewer first.")
    client = BangumiClient(access_token=token["access_token"], user_agent=user_agent())
    username = token.get("username")
    if not username:
        me = client.me()
        username = me["username"]

    print("Syncing Bangumi watched anime...")
    collections = client.watched_collections(username, max_items=max_shows)
    for item in collections:
        state.save_watched_show(collection_to_show(item))
    print(f"Saved {len(collections)} watched anime from Bangumi.")
    character_shows = 0
    character_count = 0
    for show in state.list_watched_shows(limit=max_shows):
        try:
            characters = client.subject_characters(show.bangumi_id)
        except Exception as exc:
            print(f"Bangumi character miss for {show.display_title}: {exc}")
            continue
        state.save_show_characters(show.bangumi_id, characters)
        character_shows += 1
        character_count += len(characters)
    print(f"Saved {character_count} Bangumi character names for {character_shows} shows.")

    index: AnimeOfflineIndex | None = None
    if anime_db.exists():
        print("Mapping titles through Anime Offline Database...")
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
        print(f"Mapped {mapped} watched anime to external IDs.")
    else:
        print(f"Anime database missing at {anime_db}; subtitle search will use titles only.")

    if not download_subtitles:
        return

    api_key = os.environ.get("JIMAKU_API_KEY")
    if not api_key:
        print("JIMAKU_API_KEY is not set; skipping subtitle download.")
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
            print(f"Jimaku miss for {show.display_title}: {exc}")
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
    print(f"Jimaku matched {matched} shows and cached {downloaded} subtitle files.")


def sync_lyrics(
    state_db: Path = DEFAULT_STATE_DB,
    max_albums: int | None = None,
    max_tracks: int | None = None,
) -> None:
    """Sync listened Bangumi music collections and split albums into tracks."""
    state = State(state_db)
    token = state.get_token("bangumi")
    if token is None:
        raise ValueError("Bangumi is not linked. Save Bangumi credentials in the viewer first.")
    client = BangumiClient(access_token=token["access_token"], user_agent=user_agent())
    username = token.get("username")
    if not username:
        me = client.me()
        username = me["username"]

    print("Syncing Bangumi music collections...")
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
            print(f"Bangumi subject miss for {subject.get('name') or subject_id}: {exc}")
        try:
            episodes = client.episodes(int(subject_id))
        except Exception as exc:
            print(f"Bangumi track miss for {subject.get('name') or subject_id}: {exc}")
            episodes = []
        for track in collection_to_music_tracks(item, episodes):
            if max_tracks is not None and saved_tracks >= max_tracks:
                break
            state.save_music_track(track)
            saved_tracks += 1
        if max_tracks is not None and saved_tracks >= max_tracks:
            break
    print(f"Saved {saved_tracks} tracks from {len(collections)} Bangumi music collections.")


def fetch_lyrics(
    state_db: Path = DEFAULT_STATE_DB,
    cache_dir: Path = DEFAULT_LYRICS_CACHE,
    limit: int | None = None,
    overwrite: bool = False,
    force: bool = False,
    concurrency: int = 4,
) -> None:
    """Fetch cached lyrics from LRCLIB for synced Bangumi music tracks."""
    state = State(state_db)
    tracks = state.list_music_tracks()
    if not tracks:
        print("No Bangumi music tracks yet. Use Refresh in the viewer first.")
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
            print(f"Skipping instrumental track: {track.title}")
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
                print(f"LRCLIB miss for {track.title}: {error}")
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
                print(f"LRCLIB miss for {track.title}")
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
            print(f"Cached lyrics: {track.title}")
    print(
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
        print(f"Searching LRCLIB album candidates for {len(pending)} albums...")

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
                print(f"LRCLIB album search miss for {album_title}: {error}")
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
                print(f"Cached LRCLIB album candidates: {album_title} ({len(album_results)})")
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


def export_corpus_json(
    output: Path = Path("corpus.json"),
    state_db: Path = DEFAULT_STATE_DB,
    jlpt_words: Path = DEFAULT_JLPT_WORDS,
    level: int | None = None,
    limit: int | None = None,
    examples_per_word: int = 5,
    context_lines: int = 2,
    context_min_chars: int = 40,
    context_max_lines: int | None = 4,
    zh_dict: Path = DEFAULT_ZH_DICT,
    jmdict: Path = DEFAULT_JMDICT,
    lexical_notes: bool = True,
    subtitles: list[Path] | None = None,
    texts: list[Path] | None = None,
    text_dir: Path = DEFAULT_TEXTS_DIR,
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
    )
    print(f"Wrote corpus JSON: {output}")


def fetch_anime_db(
    output: Path = DEFAULT_ANIME_DB,
) -> None:
    """Download the latest Anime Offline Database JSON release asset."""
    path = download_latest_anime_db(output)
    print(f"Downloaded Anime Offline Database: {path}")


def init_sample_jlpt(
    output: Path = DEFAULT_JLPT_WORDS,
    overwrite: bool = False,
) -> None:
    """Create a tiny sample JLPT list so the pipeline can run end to end."""
    if output.exists() and not overwrite:
        print(f"Already exists: {output}")
        return
    write_sample_jlpt(output)
    print(f"Wrote sample JLPT list: {output}")


def fetch_jlpt_words(
    output: Path = DEFAULT_JLPT_WORDS,
    source_url: str = "https://raw.githubusercontent.com/elzup/jlpt-word-list/master/out/all.csv",
) -> None:
    """Download and normalize a community JLPT vocabulary list."""
    path = download_jlpt_words(output, source_url=source_url)
    words = load_jlpt_words(path)
    counts = ", ".join(f"N{level}: {words.total_by_level(level)}" for level in range(5, 0, -1))
    print(f"Wrote JLPT word list: {path} ({counts})")


def fetch_jmdict(
    output: Path = DEFAULT_JMDICT,
    source_url: str = "http://ftp.edrdg.org/pub/Nihongo/JMdict_e_examp.gz",
) -> None:
    """Download JMdict with examples for offline word-form and usage notes."""
    path = download_jmdict(output, source_url=source_url)
    print(f"Downloaded JMdict: {path}")


def fetch_lexical_resources(
    jmdict_output: Path = DEFAULT_JMDICT,
) -> None:
    """Download offline lexical resources used by the viewer."""
    jmdict_path = download_jmdict(jmdict_output)
    print(f"Downloaded lexical resources: {jmdict_path}")


def fetch_zh_dict(
    output: Path = DEFAULT_ZH_DICT,
    source_url: str = "https://raw.githubusercontent.com/lxl66566/Japanese-Chinese-thesaurus/main/final.json",
) -> None:
    """Download a lightweight Japanese-Chinese glossary for the viewer."""
    path = download_zh_dict(output, source_url=source_url)
    wiktionary_path = download_zhwiktionary_ja_dict(DEFAULT_ZHWIKTIONARY_JA_DICT, raw_path=DEFAULT_ZHWIKTIONARY_RAW)
    glossary = ChineseGlossary.load(path)
    print(
        f"Wrote Japanese-Chinese glossary: {path}, {wiktionary_path} "
        f"({len(glossary.entries)} entries)"
    )
