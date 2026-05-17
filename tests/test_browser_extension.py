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


def test_extension_reader_toolbar_can_read_selected_paragraph() -> None:
    content = (ROOT / "browser_extension" / "content.js").read_text(encoding="utf-8")
    background = (ROOT / "browser_extension" / "background.js").read_text(encoding="utf-8")
    manifest = (ROOT / "browser_extension" / "manifest.json").read_text(encoding="utf-8")

    assert 'importSelection: "导入选中"' in content
    assert 'importArticle: "导入正文"' in content
    assert 'pickImport: "点选导入"' in content
    assert 'readAll: "朗读全文"' in content
    assert 'readParagraph: "朗读选段"' in content
    assert 'pickParagraph: "点要朗读的段落。Esc 取消。"' in content
    assert 'furigana: "假名"' in content
    assert 'switchLanguage: "EN"' in content
    assert 'stopReading: "停止"' in content
    assert "jpcorpus-reader-toolbar" in content
    assert "jpcorpus-reader-toolbar-status" in content
    assert "jpcorpus-reader-speech-button" in content
    assert "importSelectedTextFromPage" in content
    assert "importMainArticleFromPage" in content
    assert "startReaderParagraphPicker" in content
    assert "toggleReaderFurigana" in content
    assert "renderReaderTokenText" in content
    assert "positionToastUnderToolbar" in content
    assert "speakReaderParagraph" in content
    assert "readerSpeechUnitsForElement" in content
    assert "speakReaderVoicevoxUnits" in content
    assert "prepareReaderVoicevoxUnit(units[index + 1])" in content
    assert "rangeForSpeechOffsets" in content
    assert "readabilityMatchScore" in content
    assert "SYNTHESIZE_VOICEVOX" in content
    assert "SYNTHESIZE_VOICEVOX" in background
    assert "chrome.action.onClicked.addListener" in background
    assert '"default_popup"' not in manifest
    assert 'files: ["vendor/Readability.js", "content.js"]' in (ROOT / "browser_extension" / "popup.js").read_text(encoding="utf-8")
    assert 'button.textContent = tr("stopReading");' in content
    assert "resetReaderSpeechButton" in content
    assert "jpcorpus-reader-speaking" in content
