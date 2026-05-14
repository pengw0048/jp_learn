from jpcorpus.viewer_config import llm_config_status, save_viewer_config, viewer_config_status


def test_viewer_config_status_reports_missing_keys(monkeypatch):
    for key in (
        "JPCORPUS_BANGUMI_CLIENT_ID",
        "JPCORPUS_BANGUMI_CLIENT_SECRET",
        "JIMAKU_API_KEY",
        "JPCORPUS_LLM_MODEL",
        "JPCORPUS_LLM_API_KEY",
        "OPENAI_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("JPCORPUS_LLM_PROVIDER", "openai-compatible")

    status = viewer_config_status()

    assert status["services"][0]["missing"] == [
        "JPCORPUS_BANGUMI_CLIENT_ID",
        "JPCORPUS_BANGUMI_CLIENT_SECRET",
    ]
    assert status["services"][1]["missing"] == ["JIMAKU_API_KEY"]
    assert status["services"][2]["missing"] == ["JPCORPUS_LLM_MODEL", "JPCORPUS_LLM_API_KEY"]


def test_save_viewer_config_updates_dotenv(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text("JIMAKU_API_KEY=old\nUNCHANGED=yes\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("JIMAKU_API_KEY", "old")

    config = save_viewer_config(
        {
            "jimaku_api_key": "new",
            "llm_provider": "openai-compatible",
            "llm_model": "Qwen/Qwen2.5-7B-Instruct",
            "llm_base_url": "https://api.siliconflow.cn/v1",
            "llm_api_key": "sk-test",
        }
    )

    text = env_path.read_text(encoding="utf-8")
    assert "JIMAKU_API_KEY=new" in text
    assert "UNCHANGED=yes" in text
    assert "JPCORPUS_LLM_MODEL=Qwen/Qwen2.5-7B-Instruct" in text
    assert config["llm"]["provider"] == "openai-compatible"
    assert llm_config_status()["api_key_configured"] is True
