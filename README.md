# jpcorpus

`jpcorpus` is the v0.1 local app from the product spec: it connects a Bangumi watched list, maps titles to external anime IDs, downloads Japanese subtitles from Jimaku when available, builds a structured personal JLPT corpus, opens a small web viewer, and exports an Anki deck.

The MVP intentionally stays local-first and file-backed. It does not include hosted accounts, SRS scheduling, vector search, LLM annotation, video jump links, screenshots, or chat tutor flows.

## Setup

```bash
uv sync --extra japanese --extra dev
```

Register the two external services by hand:

- Bangumi application: <https://bgm.tv/dev/app>
- Jimaku API key: <https://jimaku.cc/api/docs>

Set credentials in `.env`:

```bash
cp .env.example .env
$EDITOR .env
```

Bangumi requires a useful non-default User-Agent for API clients. The default is `peng/jpcorpus-v0.1`, but setting your own is recommended.
Shell environment variables take precedence over `.env`.

## First Run

```bash
uv run jpcorpus data fetch-anime-db
uv run jpcorpus data fetch-jlpt-words
uv run jpcorpus data fetch-zh-dict
uv run jpcorpus link bangumi
uv run jpcorpus sync
uv run jpcorpus lyrics sync
uv run jpcorpus lyrics fetch
uv run jpcorpus report --level 3 --output report.md
uv run jpcorpus report --language en --level 3 --output report.en.md
uv run jpcorpus export corpus-json --output corpus.json
uv run jpcorpus view --corpus corpus.json
uv run jpcorpus export anki --level 3 --output personal-jlpt.apkg
```

`jpcorpus data fetch-jlpt-words` downloads and normalizes the MIT-licensed `elzup/jlpt-word-list` CSV data, which is based on community JLPT decks originally derived from Tanos-style lists. `jpcorpus data fetch-zh-dict` downloads the Unlicense `lxl66566/Japanese-Chinese-thesaurus` glossary for Chinese report definitions. The JLPT does not publish an official vocabulary list, so treat level coverage as an approximation rather than an exam guarantee.

Reports currently support `zh` and `en` through `--language`. User-facing strings are centralized in `jpcorpus/i18n.py` so future UI work can add more languages without chasing hard-coded report labels.

The Markdown report is a POC/debug view. `jpcorpus export corpus-json` writes the word/example/context data as structured JSON, including a `meaning_zh` field when `data/jp-zh-dict.json` is available. The JSON includes JLPT words that did not appear in the synced media as zero-count entries with no examples, so the viewer can behave like a real word list rather than only a frequency report. Corpus JSON defaults to five examples per word and keeps enough nearby subtitle or lyric blocks for LLM scene annotation, while preserving line breaks inside multi-line subtitle cues. It also stores cached Bangumi show summaries for future scene context; `jpcorpus annotate` keeps prompts source-text-only by default, and can opt into those summaries with `--use-show-context`. `jpcorpus annotate` can call any OpenAI-compatible endpoint to add example-level `translation_zh`, `usage_note_zh`, and `scene_description` fields. That includes OpenAI, a LiteLLM proxy, Ollama/Open WebUI style local servers, or a local Apple Foundation Models wrapper. `jpcorpus view` serves a local web viewer for browsing that JSON with word search, JLPT filters, source filters, examples, and browser-local study status.

Lyrics are optional local cache data, like subtitles. `jpcorpus lyrics sync` reads Bangumi music collections and splits album subjects into track rows through Bangumi episodes. `jpcorpus lyrics fetch` searches LRCLIB and stores matched synced `.lrc` or plain `.txt` files under `data/lyrics-cache/`. It first builds a versioned LRCLIB album candidate cache with album and artist query fallbacks, then scores each track so covers and remixes can still match while obvious instrumental or non-Japanese results are skipped. LRCLIB misses are cached in the local state database too, so repeated fetches skip BGM/OST misses by default; use `jpcorpus lyrics fetch --force` after matching logic changes or when you want to retry old misses. Subtitle and lyric examples stay separate in the corpus JSON through `source_type`.

Optional LLM annotation:

```bash
uv run jpcorpus annotate --provider apple \
  --input corpus.json \
  --output corpus.annotated.json \
  --limit 20
uv run jpcorpus view --corpus corpus.annotated.json
```

Use `--provider openai-compatible --model your-model` instead for OpenAI, LiteLLM, Ollama/Open WebUI, or any compatible local server. LLM annotations use the same versioned state-database cache, keyed by source text and provider context, so repeated annotation runs reuse existing results until the annotation cache version changes.

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
~/.jpcorpus/state.db           # OAuth token, watched shows, music tracks, cached file index, versioned caches
```

`jpcorpus` accepts JLPT JSON as either a list of objects or a dictionary grouped by level. Each word object can use common keys such as `word`, `surface`, `reading`, `level`, `meaning`, or `translation`.

## Notes on Mapping

Jimaku's current API searches entries by AniList ID or fuzzy title query. The Anime Offline Database does not guarantee Bangumi IDs, so this implementation tries:

1. Direct Bangumi source URL match if present in the dataset.
2. Exact normalized title + year match.
3. Exact normalized title match without year.

When no mapping is found, sync falls back to a Jimaku title search.
