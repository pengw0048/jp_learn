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
   - click Pick page area, hover a visible text block, then click it. Press `[` for a smaller block, `]` for a larger block, or Esc to cancel.
6. For temporary on-page lookup, open the popup and click Toggle page reading mode, or right-click the page and choose Toggle jpcorpus reading mode. This does not save the page; it highlights known words and shows a floating glossary panel when a highlighted word is clicked. Click Add to study in that panel to add the word to the viewer's study list.

For pages with many nested spans or ruby annotations, Add main article strips `rt`/`rp` ruby text before importing. Selecting the exact text first is still the most precise option for a small snippet.

The extension posts the selected text to `http://127.0.0.1:8767/api/import-text`, saves it under `texts/web/`, and starts a local corpus refresh. If the same text was already imported, the viewer returns the existing file and the extension skips the refresh.

Right-click imports show an in-page toast and a desktop notification when the import starts, is skipped as a duplicate, or fails. If the local viewer is not running, the toast, notification, and extension badge will say that the viewer could not be reached.

If the viewer is running on another local port, update the Local viewer URL in the extension popup.

If the popup says the local viewer returned HTML or an old API, stop the running viewer and start `uv run jpcorpus` again, then reload this extension in `chrome://extensions`.
