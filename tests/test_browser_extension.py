from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("script_name", ["background.js", "content.js", "popup.js"])
def test_browser_extension_scripts_parse(script_name: str) -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    script = ROOT / "browser_extension" / script_name
    result = subprocess.run(
        [node, "--check", str(script)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
