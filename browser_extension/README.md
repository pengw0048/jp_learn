# jpcorpus Web Importer

This unpacked Chrome extension sends selected web text to the local jpcorpus viewer.

## Use

1. Start the local viewer with `uv run jpcorpus`.
2. Open `chrome://extensions`.
3. Enable Developer mode.
4. Click Load unpacked and select this `browser_extension/` folder.
5. Select Japanese text on a webpage, then either:
   - right-click and choose Add selection to jpcorpus, or
   - open the extension popup and click Import current selection.

The extension posts the selected text to `http://127.0.0.1:8767/api/import-text`, saves it under `texts/web/`, and starts a local corpus refresh.

If the viewer is running on another local port, update the Local viewer URL in the extension popup.
