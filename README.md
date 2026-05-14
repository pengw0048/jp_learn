# jpcorpus

`jpcorpus` is the v0.1 local app from the product spec: it connects a Bangumi watched list, maps titles to external anime IDs, downloads Japanese subtitles from Jimaku when available, imports local lyrics/books, builds a structured personal JLPT corpus, and opens a small study viewer.

The MVP intentionally stays local-first and file-backed. It does not include hosted accounts, vector search, video jump links, screenshots, or chat tutor flows.

## Setup

```bash
uv sync
```

After installing, launch the app with `uv run jpcorpus`. The viewer opens at <http://127.0.0.1:8767/> by default. If `corpus.json` does not exist yet, the command creates a small starter file so the UI can open.

From the viewer, open Maintenance:

1. Fill Bangumi, Jimaku, and optional LLM settings in Configuration, then click Save config.
2. Click Refresh all for the first full build. It updates word/dictionary resources, syncs Bangumi media, fetches subtitles/lyrics, imports local `.txt`/`.epub` files from `texts/`, and regenerates `corpus.json`.
3. Later, run `uv run jpcorpus` again and use Refresh for new media/local text changes. LLM settings are only needed for on-demand AI explanations in the reader.

The normal working corpus is `corpus.json` plus its generated `corpus.index.json` sidecar. Extra input/output paths are for debugging or experiments.

External service setup:

- Bangumi application: <https://bgm.tv/dev/app>
- Jimaku API key: <https://jimaku.cc/api/docs>

You can configure credentials either in the viewer UI or by editing `.env` directly. The UI writes to the local `.env` only when the viewer is opened on `127.0.0.1`.

Manual `.env` setup:

```bash
cp .env.example .env
$EDITOR .env
```

Bangumi requires a useful non-default User-Agent for API clients. The default is `peng/jpcorpus-v0.1`, but setting your own is recommended.
Shell environment variables take precedence over `.env`.

## First Run

Normal UI path:

```bash
uv run jpcorpus
```

Then use the Maintenance panel. Day to day, this is still the only command you need.

The app intentionally does not expose a command tree. Data sync, dictionary refresh, and corpus rebuild are launched from the viewer so a normal user does not need to learn separate commands or path flags.

The Maintenance panel can update the MIT-licensed `elzup/jlpt-word-list` data, the Unlicense `lxl66566/Japanese-Chinese-thesaurus` glossary, and offline JMdict/KANJIDIC2 lexical resources. The JLPT does not publish an official vocabulary list, so treat level coverage as an approximation rather than an exam guarantee.

The viewer currently supports Chinese and English UI labels. User-facing strings are centralized in `jpcorpus/viewer_assets/app.js` so future UI work can add more languages without chasing hard-coded labels.

The app writes word/example/context data as structured JSON in `corpus.json`, including a `meaning_zh` field when `data/jp-zh-dict.json` is available. It also writes a compact `corpus.index.json` sidecar for faster viewer startup; full word examples, lexical notes, and source lines are loaded on demand. The JSON includes JLPT words that did not appear in the synced media as zero-count entries with no examples, so the viewer can behave like a real word list rather than only a frequency view. Corpus JSON defaults to five examples per word and keeps enough nearby subtitle, lyric, or text blocks for context, while preserving line breaks inside multi-line subtitle cues.

Lyrics are optional local cache data, like subtitles. Refresh syncs Bangumi music collections, splits album subjects into track rows through Bangumi episodes, searches LRCLIB, and stores matched synced `.lrc` or plain `.txt` files under `data/lyrics-cache/`. It first builds a versioned LRCLIB album candidate cache with album and artist query fallbacks, then scores each track so covers and remixes can still match while obvious instrumental or non-Japanese results are skipped. LRCLIB misses are cached in the local state database too, so repeated refreshes skip BGM/OST misses by default. Subtitle and lyric examples stay separate in the corpus JSON through `source_type`.

Local text files are optional too. Put Japanese `.txt` or `.epub` files in `texts/`, then click Refresh. The corpus importer will add them as `source_type: text`, using EPUB metadata when available and the file name as a fallback title.

Web text can be imported from the viewer Maintenance panel by pasting a title, optional URL, and selected text. The app saves the text under `texts/web/` with a sidecar metadata file, then refreshes only the imported web-text slice of the corpus. Exact duplicate web text is detected by content hash, so importing the same page or selection again reuses the existing file and skips the refresh. Imported web texts can be deleted from the Sources panel; the viewer removes the saved `.txt` and `.meta.json` files and refreshes that same web-text slice instead of reprocessing subtitles, lyrics, and books. The optional unpacked Chrome extension in `browser_extension/` adds right-click selection import, right-click main-article import using Mozilla Readability with a generic fallback, a small page-area picker, and an in-page reading mode that asks the local viewer to annotate visible Japanese text with subtle highlights and a floating glossary panel. Words can be added to the viewer study list from that floating panel. Extension imports show an in-page toast and a notification for both success and failure, so a stopped or stale local viewer is visible without opening the popup.

Optional reader AI explanation uses Anthropic, OpenAI-compatible endpoints, or Apple Foundation Models configured through `.env` or the viewer Configuration form. The Apple provider compiles `jpcorpus/apple_fm_annotate.swift` into `~/.jpcorpus/apple_fm_annotate` on first use, then keeps that worker process alive and sends JSONL requests over stdin/stdout for reader explanation requests.

## Data Files

```text
data/
  anime-offline-database.json  # cached Anime Offline Database release asset
  jlpt-words.json              # local JLPT vocabulary list
  jimaku-cache/                # downloaded .srt/.ass files
  lyrics-cache/                # downloaded .lrc/.txt lyric files
texts/                         # optional local Japanese .txt/.epub books/articles
texts/web/                     # web selections imported by the viewer or extension
browser_extension/             # optional unpacked Chrome extension for web import and page annotation
~/.jpcorpus/state.db           # OAuth token, watched shows, music tracks, cached file index, versioned caches
```

`jpcorpus` accepts JLPT JSON as either a list of objects or a dictionary grouped by level. Each word object can use common keys such as `word`, `surface`, `reading`, `level`, `meaning`, or `translation`.

## Notes on Mapping

Jimaku's current API searches entries by AniList ID or fuzzy title query. The Anime Offline Database does not guarantee Bangumi IDs, so this implementation tries:

1. Direct Bangumi source URL match if present in the dataset.
2. Exact normalized title + year match.
3. Exact normalized title match without year.

When no mapping is found, sync falls back to a Jimaku title search.
