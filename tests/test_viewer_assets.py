from __future__ import annotations

import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest


VIEWER_ASSET_DIR = Path(__file__).resolve().parents[1] / "jpcorpus" / "viewer_assets"


class ScriptParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.scripts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "script":
            return
        attrs_by_name = dict(attrs)
        src = attrs_by_name.get("src")
        if src:
            self.scripts.append(src)


def viewer_script_sources() -> list[str]:
    parser = ScriptParser()
    parser.feed((VIEWER_ASSET_DIR / "index.html").read_text(encoding="utf-8"))
    return parser.scripts


def test_viewer_index_references_existing_scripts_in_loader_order():
    sources = viewer_script_sources()

    assert sources[-1] == "/app.js"
    assert len(sources) == len(set(sources))
    assert "/app_storage.js" in sources
    assert "/app_i18n.js" in sources
    assert "/app_dom.js" in sources
    assert "/app_api.js" in sources
    assert "/app_detail.js" in sources

    app_index = sources.index("/app.js")
    for source in sources:
        assert source.startswith("/")
        script_path = VIEWER_ASSET_DIR / source.lstrip("/")
        assert script_path.is_file()
        if source != "/app.js":
            assert sources.index(source) < app_index


def test_viewer_javascript_files_parse_with_node():
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")

    for script_path in sorted(VIEWER_ASSET_DIR.glob("*.js")):
        subprocess.run(
            [node, "--check", str(script_path)],
            check=True,
            capture_output=True,
            text=True,
        )
