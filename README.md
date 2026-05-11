# jpcorpus

`jpcorpus` is the v0.1 local app from the product spec: it connects a Bangumi watched list, maps titles to external anime IDs, downloads Japanese subtitles from Jimaku when available, imports local lyrics/books, builds a structured personal JLPT corpus, opens a small study viewer, and exports an Anki deck.

The MVP intentionally stays local-first and file-backed. It does not include hosted accounts, vector search, video jump links, screenshots, or chat tutor flows.

## Setup

```bash
uv sync --extra japanese --extra dev
```

After installing, launch the app with `uv run jpcorpus view`. The viewer opens at <http://127.0.0.1:8767/> by default. If `corpus.json` does not exist yet, the command creates a small starter file so the UI can open.

From the viewer, open Maintenance:

1. Fill Bangumi, Jimaku, and optional LLM settings in Configuration, then click Save config.
2. Click Refresh all for the first full build. It updates word/dictionary resources, syncs Bangumi media, fetches subtitles/lyrics, imports local `.txt`/`.epub` files from `texts/`, and regenerates `corpus.json`.
3. Later, run `uv run jpcorpus view` again and use Refresh for new media/local text changes. Use LLM annotation only when you want paid/local model annotation.

The only normal working corpus file is `corpus.json`. Extra input/output paths are for debugging or experiments.

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
uv run jpcorpus view
```

Then use the Maintenance panel. Day to day, this is still the only command you need.

Advanced command-line equivalent:

```bash
uv run jpcorpus data fetch-anime-db
uv run jpcorpus data fetch-jlpt-words
uv run jpcorpus data fetch-zh-dict
uv run jpcorpus data fetch-lexical-resources
uv run jpcorpus link bangumi
uv run jpcorpus sync
uv run jpcorpus lyrics sync
uv run jpcorpus lyrics fetch
uv run jpcorpus export corpus-json --output corpus.json
uv run jpcorpus view
```

Optional debug/export commands:

```bash
uv run jpcorpus report --level 3 --output report.md
uv run jpcorpus report --language en --level 3 --output report.en.md
uv run jpcorpus export anki --level 3 --output personal-jlpt.apkg
```

`jpcorpus data fetch-jlpt-words` downloads and normalizes the MIT-licensed `elzup/jlpt-word-list` CSV data, which is based on community JLPT decks originally derived from Tanos-style lists. `jpcorpus data fetch-zh-dict` downloads the Unlicense `lxl66566/Japanese-Chinese-thesaurus` glossary for Chinese report definitions. The JLPT does not publish an official vocabulary list, so treat level coverage as an approximation rather than an exam guarantee.

Reports currently support `zh` and `en` through `--language`. User-facing strings are centralized in `jpcorpus/i18n.py` so future UI work can add more languages without chasing hard-coded report labels.

The Markdown report is a POC/debug view. `jpcorpus export corpus-json` writes the word/example/context data as structured JSON, including a `meaning_zh` field when `data/jp-zh-dict.json` is available. The JSON includes JLPT words that did not appear in the synced media as zero-count entries with no examples, so the viewer can behave like a real word list rather than only a frequency report. Corpus JSON defaults to five examples per word and keeps enough nearby subtitle, lyric, or text blocks for LLM annotation, while preserving line breaks inside multi-line subtitle cues. It also stores cached Bangumi show summaries for future prompt context; `jpcorpus annotate` keeps prompts source-text-only by default, and can opt into those summaries with `--use-show-context`. `jpcorpus annotate` can add example-level `translation_zh` and `usage_note_zh` fields through Anthropic Claude, any OpenAI-compatible endpoint, or a local Apple Foundation Models wrapper. `jpcorpus view` serves a local web viewer for browsing that JSON with word search, JLPT filters, source filters, examples, and browser-local study status.

Lyrics are optional local cache data, like subtitles. `jpcorpus lyrics sync` reads Bangumi music collections and splits album subjects into track rows through Bangumi episodes. `jpcorpus lyrics fetch` searches LRCLIB and stores matched synced `.lrc` or plain `.txt` files under `data/lyrics-cache/`. It first builds a versioned LRCLIB album candidate cache with album and artist query fallbacks, then scores each track so covers and remixes can still match while obvious instrumental or non-Japanese results are skipped. LRCLIB misses are cached in the local state database too, so repeated fetches skip BGM/OST misses by default; use `jpcorpus lyrics fetch --force` after matching logic changes or when you want to retry old misses. Subtitle and lyric examples stay separate in the corpus JSON through `source_type`.

Local text files are optional too. Put Japanese `.txt` or `.epub` files in `texts/` and `jpcorpus export corpus-json` will import them automatically as `source_type: text`, using the file name as the title. You can also pass one-off files with `--text path/to/book.epub`; those examples appear in the viewer under the Text source filter.

Optional LLM annotation can be run from the viewer Maintenance panel. The CLI equivalent is:

```bash
uv run jpcorpus annotate --provider apple --limit 20
uv run jpcorpus view
```

Use `--provider anthropic` to try Claude Haiku through `ANTHROPIC_API_KEY`; it defaults to `claude-haiku-4-5-20251001` when `--model` and `ANTHROPIC_MODEL` are omitted, and uses `ANTHROPIC_BASE_URL` for custom Anthropic-compatible gateways. Add `--concurrency 4` for parallel remote annotation requests, or use `--rpm 40` to stay under a provider request-per-minute limit; successful annotations are written to the versioned state-database cache as each request completes, and failed requests are reported without stopping the batch. Use `--provider openai-compatible --model your-model` or `JPCORPUS_LLM_MODEL` instead for OpenAI, LiteLLM, Ollama/Open WebUI, or any compatible local server. LLM annotations are keyed by source text and provider context, so repeated annotation runs reuse existing results until the annotation cache version changes.

To preview only the annotations already stored in the local cache without making any LLM requests, add `--cache-only`. This is useful for partially annotated corpora:

```bash
uv run jpcorpus annotate --cache-only --limit 10000
```

By default, annotation updates `corpus.json` in place. Use `--input` and `--output` only when you want a separate experimental file.

The Apple provider compiles `jpcorpus/apple_fm_annotate.swift` into `~/.jpcorpus/apple_fm_annotate` on first use, then keeps that worker process alive and sends JSONL requests over stdin/stdout during the annotation run.

## Local Smoke Test Without API Keys

```bash
uv run jpcorpus data init-sample-jlpt --overwrite
uv run jpcorpus report \
  --language zh \
  --jlpt-words data/jlpt-words.json \
  --subtitles tests/fixtures/sample.srt \
  --output /tmp/jpcorpus-report.zh.md
uv run jpcorpus report \
  --language en \
  --jlpt-words data/jlpt-words.json \
  --subtitles tests/fixtures/sample.srt \
  --output /tmp/jpcorpus-report.en.md
uv run jpcorpus export anki \
  --jlpt-words data/jlpt-words.json \
  --subtitles tests/fixtures/sample.srt \
  --output /tmp/jpcorpus-smoke.apkg
uv run jpcorpus export corpus-json \
  --jlpt-words data/jlpt-words.json \
  --subtitles tests/fixtures/sample.srt \
  --output /tmp/jpcorpus-smoke.json
uv run jpcorpus view --corpus /tmp/jpcorpus-smoke.json --port 8765
```

## Data Files

```text
data/
  anime-offline-database.json  # cached Anime Offline Database release asset
  jlpt-words.json              # local JLPT vocabulary list
  jimaku-cache/                # downloaded .srt/.ass files
  lyrics-cache/                # downloaded .lrc/.txt lyric files
texts/                         # optional local Japanese .txt/.epub books/articles
~/.jpcorpus/state.db           # OAuth token, watched shows, music tracks, cached file index, versioned caches
```

`jpcorpus` accepts JLPT JSON as either a list of objects or a dictionary grouped by level. Each word object can use common keys such as `word`, `surface`, `reading`, `level`, `meaning`, or `translation`.

## Notes on Mapping

Jimaku's current API searches entries by AniList ID or fuzzy title query. The Anime Offline Database does not guarantee Bangumi IDs, so this implementation tries:

1. Direct Bangumi source URL match if present in the dataset.
2. Exact normalized title + year match.
3. Exact normalized title match without year.

When no mapping is found, sync falls back to a Jimaku title search.
