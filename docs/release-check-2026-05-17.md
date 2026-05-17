# Release Check Report - 2026-05-17

Baseline commit: `1d843b0`

Run time: 2026-05-17 19:55 EDT

## Verdict

The current build is a good release-candidate POC. Automated checks, local service checks, corpus shard checks, local dictionary checks, extension static checks, and VOICEVOX API checks passed.

Manual visual confirmation is still recommended before tagging because the Codex in-app browser automation was unavailable in this desktop session, so the main UI and Chrome extension were not clicked through visually.

## Repository Hygiene

- PASS: `git status --short` was clean before starting the check.
- PASS: `.env`, `.env.*`, imported texts, EPUBs, generated corpus files, corpus shards, subtitle cache, lyric cache, and large dictionary/resource files are ignored.
- PASS: tracked files do not contain API key values matching the checked secret patterns.
- PASS: local private files are present but untracked/ignored: `.env`, EPUB input, `corpus.json`, `corpus.index.json`, and generated annotated corpus files.
- FIXED: `docs/release-checklist.md` referenced `browser_extension/content_script.js`; the real file is `browser_extension/content.js`.

## Automated Checks

- PASS: `uv sync --extra dev`
- PASS: `node --check jpcorpus/viewer_assets/app.js`
- PASS: `node --check jpcorpus/viewer_assets/app_i18n.js`
- PASS: `uv run --extra dev pytest -q` (`140 passed`)
- PASS: `node --check browser_extension/background.js`
- PASS: `node --check browser_extension/content.js`
- PASS: `node --check browser_extension/popup.js`
- PASS: `node --check browser_extension/vendor/Readability.js`
- PASS: `uv run --extra dev pytest tests/test_browser_extension.py -q` (`6 passed`)

## Local Service

- PASS: `http://127.0.0.1:8767/healthz` returned `ok`.
- PASS: `http://127.0.0.1:8767/` served the viewer shell.
- PASS: `corpus.index.json` loaded through the local server.
- PASS: `/api/maintenance` responded and reported Maintenance enabled.
- PASS: `/api/jobs/current` returned no running job.

## Current Corpus Snapshot

- Generated at: `2026-05-17T00:18:06`
- Words in compact index: `11,643`
- Sources: `102`
- Subtitle files: `77`
- Lyric files: `21`
- Text files: `4`
- Total tokens: `210,727`
- Unique token count: `9,971`
- Missing Chinese meaning count: `1,418`
- English-only word count: `1,373`

## Configuration and Integrations

- PASS: Bangumi is configured according to `/api/maintenance`.
- PASS: Jimaku is configured according to `/api/maintenance`.
- PASS: LLM is configured according to `/api/maintenance`.
- NOT RUN: LLM explanation was not invoked to avoid spending tokens during a release check.
- PASS: VOICEVOX engine is reachable at `127.0.0.1:50021` and `localhost:50021`.
- PASS: `/api/tts/voicevox-speakers` returned speakers.
- PASS: `/api/tts/voicevox` generated a WAV response for a short Japanese phrase.

## Local Dictionaries

- PASS: `/api/dictionaries` returned three ready and enabled dictionaries.
- PASS: Yomitan dictionary `wty-ja-zh` is ready.
- PASS: MDX dictionary `小學館V2日漢辭典` is ready.
- PASS: MDX dictionary `新日漢大辭典` is ready.
- PASS: Word detail API returned local dictionary results for representative words.
- NOT RUN: enable/disable/delete/reindex actions were not executed because they mutate the user's current dictionary setup.

## Word Detail Smoke Tests

- PASS: `言う` loaded with reading, level, Chinese meaning, 5 examples, and local dictionary results.
- PASS: `諦める` loaded with reading, level, Chinese meaning, 5 examples, and local dictionary results.
- PASS: `ありがとう` loaded with reading, level, Chinese meaning, and local dictionary results.

## Source Reader Smoke Tests

- PASS: Subtitle source detail loaded: `CLANNAD`, 367 lines.
- PASS: Lyric source detail loaded: `-影二つ- (short ver.)`, 26 lines.
- PASS: Text source detail loaded: imported NHK text, 30 lines.

## Study Flow

- PASS: Automated tests cover selected-level bulk study actions.
- PASS: Static check confirms selected-level add and clear actions ignore source/search filters.
- NOT RUN: Live UI clicks for `Add all N2` and `Clear N2` were not executed to avoid mutating the user's study queue during the check.
- PASS: `/api/study-state` responded successfully.

## Browser Extension

- PASS: Manifest is valid JSON and uses Manifest V3.
- PASS: Extension declares expected permissions and local host permissions.
- PASS: Background, popup, content script, and Readability vendor script parse successfully.
- PASS: Extension unit/static tests passed.
- NOT RUN: Live Chrome extension install and page annotation click-through were not executed in this automated pass.

## Visual UI Check

- BLOCKED: Codex in-app browser automation could not open a pane in this session: `No active Codex browser pane available`.
- Manual follow-up recommended: open <http://127.0.0.1:8767/> and quickly click Study, Browse, Reader, Maintenance, local dictionary detail, and read-aloud controls.

## Recommended Before Tagging

1. Manually click through the viewer once in a real browser.
2. Manually toggle the Chrome extension toolbar on an NHK page once.
3. Decide whether to tag this build as `v0.1.0`.
