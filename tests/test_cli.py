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

    created = cli.ensure_viewer_corpus(corpus)

    payload = json.loads(corpus.read_text(encoding="utf-8"))
    assert created is True
    assert payload["schema_version"] == 13
    assert payload["summary"]["show_count"] == 0
    assert payload["words"] == []
    assert "Created starter corpus" in capsys.readouterr().out


def test_ensure_viewer_corpus_leaves_existing_file(tmp_path, capsys):
    corpus = tmp_path / "corpus.json"
    corpus.write_text('{"words": [{"word": "行く"}], "sources": []}', encoding="utf-8")

    created = cli.ensure_viewer_corpus(corpus)

    assert created is False
    assert json.loads(corpus.read_text(encoding="utf-8"))["words"] == [{"word": "行く"}]
    assert capsys.readouterr().out == ""


def test_is_empty_viewer_corpus_detects_starter_and_content(tmp_path):
    corpus = tmp_path / "corpus.json"
    cli.ensure_viewer_corpus(corpus)
    assert cli.is_empty_viewer_corpus(corpus) is True

    corpus.write_text(
        json.dumps(
            {
                "summary": {"unique_tokens": 1},
                "words": [{"word": "行く"}],
                "sources": [],
            }
        ),
        encoding="utf-8",
    )
    assert cli.is_empty_viewer_corpus(corpus) is False


def test_launch_viewer_prints_first_run_hint_for_empty_existing_corpus(
    tmp_path, monkeypatch, capsys
):
    corpus = tmp_path / "corpus.json"
    cli.ensure_viewer_corpus(corpus)
    capsys.readouterr()
    served = {}

    def fake_serve_viewer(path, *, host, port, open_browser, echo):
        served.update(
            {
                "path": path,
                "host": host,
                "port": port,
                "open_browser": open_browser,
            }
        )

    monkeypatch.setattr(cli, "serve_viewer", fake_serve_viewer)

    cli.launch_viewer(corpus, host="127.0.0.1", port=8767, open_browser=False)

    assert served == {
        "path": corpus,
        "host": "127.0.0.1",
        "port": 8767,
        "open_browser": False,
    }
    assert cli.FIRST_RUN_HINT in capsys.readouterr().out
