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


def test_popup_keeps_success_feedback_after_selection_import() -> None:
    popup = (ROOT / "browser_extension" / "popup.js").read_text(encoding="utf-8")

    assert 'alreadyImported: "已经导入过 {title}。"' in popup
    assert 'imported: "已导入 {title}。"' in popup
    assert "refs.status.textContent = importResultMessage(response.result);" in popup
    assert 'refs.status.textContent = "";' not in popup


def test_extension_reader_panel_can_read_current_sentence() -> None:
    content = (ROOT / "browser_extension" / "content.js").read_text(encoding="utf-8")

    assert 'readSentence: "朗读"' in content
    assert 'stopReading: "停止"' in content
    assert "jpcorpus-reader-speech-button" in content
    assert "activeReaderSpeechButton" in content
    assert 'button.textContent = tr("stopReading");' in content
    assert "resetReaderSpeechButton" in content
    assert "jpcorpus-reader-speaking" in content
