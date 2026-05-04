# jpcorpus

`jpcorpus` is the v0.1 CLI from the product spec: it connects a Bangumi watched list, maps titles to external anime IDs, downloads Japanese subtitles from Jimaku when available, builds a personal JLPT frequency report, and exports an Anki deck.

The MVP intentionally stays local-first and CLI-only. It does not include web UI, SRS scheduling, vector search, LLM annotation, video jump links, screenshots, or chat tutor flows.

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
uv run jpcorpus data init-sample-jlpt
uv run jpcorpus link bangumi
uv run jpcorpus sync
uv run jpcorpus report --level 3 --output report.md
uv run jpcorpus report --language en --level 3 --output report.en.md
uv run jpcorpus export anki --level 3 --output personal-jlpt.apkg
```

Replace `data/jlpt-words.json` with a real JLPT word list before trusting the coverage numbers. The sample list exists only to make the pipeline runnable.

Reports currently support `zh` and `en` through `--language`. User-facing strings are centralized in `jpcorpus/i18n.py` so future UI work can add more languages without chasing hard-coded report labels.

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
```

## Data Files

```text
data/
  anime-offline-database.json  # cached Anime Offline Database release asset
  jlpt-words.json              # local JLPT vocabulary list
  jimaku-cache/                # downloaded .srt/.ass files
~/.jpcorpus/state.db           # OAuth token, watched shows, subtitle file index
```

`jpcorpus` accepts JLPT JSON as either a list of objects or a dictionary grouped by level. Each word object can use common keys such as `word`, `surface`, `reading`, `level`, `meaning`, or `translation`.

## Notes on Mapping

Jimaku's current API searches entries by AniList ID or fuzzy title query. The Anime Offline Database does not guarantee Bangumi IDs, so this implementation tries:

1. Direct Bangumi source URL match if present in the dataset.
2. Exact normalized title + year match.
3. Exact normalized title match without year.

When no mapping is found, sync falls back to a Jimaku title search.
