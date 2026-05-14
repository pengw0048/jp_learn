# jpcorpus Web Importer

This unpacked Chrome extension sends selected web text to the local jpcorpus viewer and can annotate Japanese text directly on the current page.

## Use

1. Start the local viewer with `uv run jpcorpus`.
2. Open `chrome://extensions`.
3. Enable Developer mode.
4. Click Load unpacked and select this `browser_extension/` folder.
5. Import Japanese text from a webpage:
   - right-click and choose Add selection to jpcorpus, or
   - right-click the page and choose Add main article to jpcorpus, or
   - open the extension popup and click Import current selection, or
   - click Pick page area, hover a visible text block, then click it. Press Esc to cancel.
6. For temporary on-page lookup, open the popup and click Toggle page reading mode, or right-click the page and choose Toggle jpcorpus reading mode. This does not save the page; it annotates words that match the local glossary and shows a floating glossary panel when an annotated word is clicked. Use the status buttons in that panel to add the word to review, mark it known, ignore it, or clear the local mark.

The popup language switch controls popup labels, context menu labels, in-page toasts, and the floating glossary panel. The extension UI uses a Chinese CJK font stack first so Chinese glossary text is not accidentally rendered with Japanese glyph variants from the host page.

The popup keeps the local viewer URL in Settings. Most users can leave it at `http://127.0.0.1:8767`; change it only if the viewer is running on another local port.

Add main article uses Mozilla Readability first, then falls back to the extension's generic visible-text picker logic. For pages with many nested spans or ruby annotations, imported article text strips `rt`/`rp` ruby text before saving. Selecting the exact text first is still the most precise option for a small snippet.

The extension posts the selected text to `http://127.0.0.1:8767/api/import-text`, saves it under `texts/web/`, and starts a local imported-text refresh. If the same text was already imported, the viewer returns the existing file and the extension skips the refresh.

Right-click imports show transient in-page toasts when importing, imported, or skipped as a duplicate. Successful imports leave the extension popup status and badge clear; failures persist the popup status, show a desktop notification, and show a small badge marker so the error is easier to notice.

If the popup says the local viewer returned HTML or an old API, stop the running viewer and start `uv run jpcorpus` again, then reload this extension in `chrome://extensions`.
