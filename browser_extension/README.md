# jpcorpus Web Importer

This unpacked Chrome extension sends selected web text to the local jpcorpus viewer and can annotate Japanese text directly on the current page.

## Use

1. Start the local viewer with `uv run jpcorpus`.
2. Open `chrome://extensions`.
3. Enable Developer mode.
4. Click Load unpacked and select this `browser_extension/` folder.
5. Click the jpcorpus extension icon to show or hide the floating page toolbar.
6. Import Japanese text from a webpage:
   - right-click and choose Add selection to jpcorpus, or
   - right-click the page and choose Add main article to jpcorpus, or
   - use Import selection, Import article, or Pick import in the floating toolbar.
7. For temporary on-page lookup, use the floating toolbar or right-click the page and choose Toggle jpcorpus reading mode. This does not save the page; it annotates words that match the local glossary and shows a floating glossary panel when an annotated word is clicked. Use the status buttons in that panel to add the word to review, mark it known, ignore it, or clear the local mark. The floating reader toolbar can read the full page area or a picked passage aloud, and can toggle temporary furigana. Speech highlights the current sentence, tries the local viewer's VOICEVOX endpoint first, and falls back to browser speech.

The toolbar language switch controls toolbar labels, context menu labels, in-page toasts, and the floating glossary panel. The extension UI uses a Chinese CJK font stack first so Chinese glossary text is not accidentally rendered with Japanese glyph variants from the host page.

The extension uses `http://127.0.0.1:8767` as the local viewer URL by default.

Add main article uses Mozilla Readability first, then falls back to the extension's generic visible-text picker logic. For pages with many nested spans or ruby annotations, imported article text strips `rt`/`rp` ruby text before saving. Selecting the exact text first is still the most precise option for a small snippet.

The extension posts the selected text to `http://127.0.0.1:8767/api/import-text`, saves it under `texts/web/`, and starts a local imported-text refresh. If the same text was already imported, the viewer returns the existing file and the extension skips the refresh.

Right-click and toolbar imports show transient in-page toasts when importing, imported, or skipped as a duplicate. Successful imports leave the extension badge clear; failures show a desktop notification and a small badge marker so the error is easier to notice.

If the extension says the local viewer returned HTML or an old API, stop the running viewer and start `uv run jpcorpus` again, then reload this extension in `chrome://extensions`.
