# Release Freeze Checklist

Use this checklist before tagging or treating a build as a stable local POC.

## 1. Repository Hygiene

- [ ] `git status --short` is clean before the final commit.
- [ ] `.env`, `.env.*`, imported texts, EPUBs, dictionaries, caches, and generated corpus files are ignored.
- [ ] No API keys, personal book files, imported articles, or local dictionary payloads are staged.
- [ ] README setup still matches the current UI-first workflow.

## 2. Automated Checks

```bash
uv sync --extra dev
node --check jpcorpus/viewer_assets/app.js
node --check jpcorpus/viewer_assets/app_i18n.js
uv run --extra dev pytest -q
```

Optional extension syntax check:

```bash
node --check browser_extension/background.js
node --check browser_extension/content.js
node --check browser_extension/popup.js
```

## 3. First-Run Flow

- [ ] Start the app with `uv run jpcorpus`.
- [ ] Open <http://127.0.0.1:8767/>.
- [ ] If no corpus exists, the starter corpus opens instead of a broken page.
- [ ] Maintenance shows configuration status without requiring CLI-only steps.
- [ ] Full refresh can be started from Maintenance.
- [ ] Refresh can be started after the first full refresh.

## 4. Study Flow

- [ ] Study mode opens without selecting a random word when the queue is empty.
- [ ] Selecting `N2` shows level-level actions, not source/search filtered bulk actions.
- [ ] `Add all N2` adds unmarked N2 words to the study queue.
- [ ] `Clear N2` removes studying or uncertain N2 words without changing known or ignored words.
- [ ] Word status buttons are mutually sensible: learning, uncertain, known, ignored, and clear state do not conflict visually.
- [ ] A word added from Browse, Reader, or the browser extension appears in the study queue after state sync.
- [ ] Study progress can advance toward the 7-step target.

## 5. Reader Flow

- [ ] Subtitles, lyrics, EPUB/text, and web imports can each open in Reader mode when present.
- [ ] Switching source or highlight level does not unexpectedly reset reading position.
- [ ] Clicking empty reader space clears the selected word.
- [ ] Clicking a token resets the right-side detail scroll and shows the correct word.
- [ ] Furigana toggle works and is visually discoverable near read-aloud controls.
- [ ] Full read-aloud can start from the current line and stop from the same button.
- [ ] Single-line read-aloud works.
- [ ] Switching modes or sources stops current speech.

## 6. Dictionary Flow

- [ ] Built-in meanings remain compact in the main detail view.
- [ ] Local dictionary summaries stay short.
- [ ] Local dictionary detail opens in a modal and preserves the dictionary's original HTML formatting.
- [ ] Detail modal closes by outside click, close button, and `Esc`.
- [ ] Enabling, disabling, deleting, or rebuilding a local dictionary does not require regenerating the corpus.
- [ ] Chinese UI does not promote English fallback meanings as the primary display when Chinese meanings are available.

## 7. Browser Extension Flow

- [ ] Load `browser_extension/` as an unpacked Chrome extension.
- [ ] The extension connects to <http://127.0.0.1:8767/>.
- [ ] Right-click importing selected text gives a clear toast and avoids duplicate-looking stale status.
- [ ] Right-click importing the main article body produces usable text for at least one NHK-style page.
- [ ] Page annotation can be toggled from the floating toolbar.
- [ ] The floating glossary card shows meaning and study status.
- [ ] Study actions in the extension sync back to the main app.
- [ ] Web read-aloud and furigana controls match the main reader closely enough to feel like the same product.

## 8. Optional Integrations

- [ ] Browser Japanese voice works at least as a fallback.
- [ ] VOICEVOX works when a local engine is running on `127.0.0.1:50021`.
- [ ] Optional LLM explanation button fails gracefully when no provider is configured.
- [ ] Imported Yomitan zip dictionaries can be enabled and queried.
- [ ] Imported MDX dictionaries can be enabled and queried, except unsupported compression formats.

## 9. Final Freeze

- [ ] Run automated checks again after any final fix.
- [ ] Commit with a concise English message.
- [ ] Push `main`.
- [ ] Optionally tag the stable POC:

```bash
git tag v0.1.0
git push origin v0.1.0
```
