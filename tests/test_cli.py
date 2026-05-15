import json

import pytest

from jpcorpus import cli


def test_main_help_has_no_command_tree(capsys):
    cli.main(["--help"])

    output = capsys.readouterr().out
    assert "Usage: jpcorpus [OPTIONS]" in output
    assert "COMMAND" not in output


def test_main_rejects_extra_arguments(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["view"])

    captured = capsys.readouterr()
    assert exc.value.code == 2
    assert "Unknown argument: view" in captured.err


def test_ensure_viewer_corpus_creates_starter_corpus(tmp_path, capsys):
    corpus = tmp_path / "corpus.json"

    cli.ensure_viewer_corpus(corpus)

    payload = json.loads(corpus.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 13
    assert payload["summary"]["show_count"] == 0
    assert payload["words"] == []
    assert "Created starter corpus" in capsys.readouterr().out
