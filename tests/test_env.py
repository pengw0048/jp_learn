import os
from pathlib import Path

from jpcorpus.env import load_dotenv


def test_load_dotenv_does_not_override_existing_env(tmp_path: Path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "JIMAKU_API_KEY=from-file\n"
        "QUOTED='hello world'\n"
        "INLINE=value # comment\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("JIMAKU_API_KEY", "from-shell")

    load_dotenv(env_path)

    assert os.environ["JIMAKU_API_KEY"] == "from-shell"
    assert os.environ["QUOTED"] == "hello world"
    assert os.environ["INLINE"] == "value"

