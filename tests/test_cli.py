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
