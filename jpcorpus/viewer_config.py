from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .llm import (
    DEFAULT_ANTHROPIC_BASE_URL,
    DEFAULT_ANTHROPIC_MODEL,
    AnthropicClient,
    AppleFoundationModelsClient,
    LLMConfig,
    OpenAICompatibleClient,
)


ALLOWED_PROVIDERS = {"openai-compatible", "anthropic", "apple"}
CONFIG_ENV_PATH = Path(".env")


def viewer_config_status() -> dict[str, Any]:
    bangumi_missing = [
        key
        for key in ("JPCORPUS_BANGUMI_CLIENT_ID", "JPCORPUS_BANGUMI_CLIENT_SECRET")
        if not os.environ.get(key)
    ]
    jimaku_missing = [] if os.environ.get("JIMAKU_API_KEY") else ["JIMAKU_API_KEY"]
    llm = llm_config_status()
    llm_missing = llm_missing_keys(llm["provider"])
    return {
        "env_path": str(CONFIG_ENV_PATH.resolve()),
        "services": [
            {
                "id": "bangumi",
                "label": "Bangumi",
                "configured": not bangumi_missing,
                "missing": bangumi_missing,
            },
            {
                "id": "jimaku",
                "label": "Jimaku subtitles",
                "configured": not jimaku_missing,
                "missing": jimaku_missing,
            },
            {
                "id": "llm",
                "label": "AI explanation",
                "configured": not llm_missing,
                "missing": llm_missing,
            },
        ],
        "llm": llm,
    }


def llm_config_status() -> dict[str, Any]:
    provider = os.environ.get("JPCORPUS_LLM_PROVIDER", "openai-compatible")
    if provider == "anthropic":
        model = os.environ.get("ANTHROPIC_MODEL") or DEFAULT_ANTHROPIC_MODEL
        base_url = (
            os.environ.get("JPCORPUS_ANTHROPIC_BASE_URL")
            or os.environ.get("ANTHROPIC_BASE_URL")
            or DEFAULT_ANTHROPIC_BASE_URL
        )
        api_key_configured = bool(os.environ.get("ANTHROPIC_API_KEY"))
    elif provider == "apple":
        model = "apple"
        base_url = ""
        api_key_configured = True
    else:
        provider = "openai-compatible"
        model = os.environ.get("JPCORPUS_LLM_MODEL") or ""
        base_url = os.environ.get("JPCORPUS_LLM_BASE_URL", "https://api.openai.com/v1")
        api_key_configured = bool(
            os.environ.get("JPCORPUS_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
        )
    return {
        "provider": provider,
        "model": model,
        "base_url": base_url,
        "api_key_configured": api_key_configured,
    }


def llm_missing_keys(provider: str) -> list[str]:
    if provider == "apple":
        return []
    if provider == "anthropic":
        return ["ANTHROPIC_API_KEY"] if not os.environ.get("ANTHROPIC_API_KEY") else []
    missing = []
    if not os.environ.get("JPCORPUS_LLM_MODEL"):
        missing.append("JPCORPUS_LLM_MODEL")
    if not (os.environ.get("JPCORPUS_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")):
        missing.append("JPCORPUS_LLM_API_KEY")
    return missing


def save_viewer_config(raw: dict[str, Any]) -> dict[str, Any]:
    updates: dict[str, str] = {}
    add_optional_update(updates, "JPCORPUS_BANGUMI_CLIENT_ID", raw.get("bangumi_client_id"))
    add_optional_update(updates, "JPCORPUS_BANGUMI_CLIENT_SECRET", raw.get("bangumi_client_secret"))
    add_optional_update(updates, "JIMAKU_API_KEY", raw.get("jimaku_api_key"))
    provider = str(raw.get("llm_provider") or "").strip()
    if provider:
        if provider not in ALLOWED_PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider}")
        updates["JPCORPUS_LLM_PROVIDER"] = provider
    else:
        provider = os.environ.get("JPCORPUS_LLM_PROVIDER", "openai-compatible")
    llm_model = raw.get("llm_model")
    llm_base_url = raw.get("llm_base_url")
    llm_api_key = raw.get("llm_api_key")
    if provider == "anthropic":
        add_optional_update(updates, "ANTHROPIC_MODEL", llm_model)
        add_optional_update(updates, "ANTHROPIC_BASE_URL", llm_base_url)
        add_optional_update(updates, "ANTHROPIC_API_KEY", llm_api_key)
    elif provider == "openai-compatible":
        add_optional_update(updates, "JPCORPUS_LLM_MODEL", llm_model)
        add_optional_update(updates, "JPCORPUS_LLM_BASE_URL", llm_base_url)
        add_optional_update(updates, "JPCORPUS_LLM_API_KEY", llm_api_key)
    if updates:
        write_env_updates(CONFIG_ENV_PATH, updates)
        os.environ.update(updates)
    return viewer_config_status()


def add_optional_update(updates: dict[str, str], key: str, value: Any) -> None:
    if value is None:
        return
    text = str(value).strip()
    if text:
        updates[key] = text


def write_env_updates(path: Path, updates: dict[str, str]) -> None:
    remaining = dict(updates)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    rewritten: list[str] = []
    for line in lines:
        key = env_line_key(line)
        if key and key in remaining:
            rewritten.append(f"{key}={quote_env_value(remaining.pop(key))}")
        else:
            rewritten.append(line)
    if remaining:
        if rewritten and rewritten[-1].strip():
            rewritten.append("")
        rewritten.append("# Added by the local jpcorpus viewer.")
        for key, value in remaining.items():
            rewritten.append(f"{key}={quote_env_value(value)}")
    path.write_text("\n".join(rewritten).rstrip() + "\n", encoding="utf-8")


def env_line_key(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key, _value = stripped.split("=", 1)
    key = key.strip()
    return key or None


def quote_env_value(value: str) -> str:
    if value and all(char.isalnum() or char in "-_./:@+" for char in value):
        return value
    return json.dumps(value, ensure_ascii=False)


def resolve_llm_client(*, provider: str, model: Any = None, use_show_context: bool = False) -> Any:
    if provider == "apple":
        return AppleFoundationModelsClient(use_show_context=use_show_context)
    if provider == "anthropic":
        resolved_model = model or os.environ.get("ANTHROPIC_MODEL") or DEFAULT_ANTHROPIC_MODEL
        base_url = (
            os.environ.get("JPCORPUS_ANTHROPIC_BASE_URL")
            or os.environ.get("ANTHROPIC_BASE_URL")
            or DEFAULT_ANTHROPIC_BASE_URL
        )
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("Set ANTHROPIC_API_KEY before using Anthropic AI explanation.")
        return AnthropicClient(
            LLMConfig(
                model=resolved_model,
                base_url=base_url,
                api_key=api_key,
                use_show_context=use_show_context,
            )
        )
    if provider == "openai-compatible":
        resolved_model = model or os.environ.get("JPCORPUS_LLM_MODEL")
        if not resolved_model:
            raise ValueError("Set JPCORPUS_LLM_MODEL before using OpenAI-compatible AI explanation.")
        base_url = os.environ.get("JPCORPUS_LLM_BASE_URL", "https://api.openai.com/v1")
        api_key = os.environ.get("JPCORPUS_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if "api.openai.com" in base_url and not api_key:
            raise ValueError("Set JPCORPUS_LLM_API_KEY or OPENAI_API_KEY before using AI explanation.")
        return OpenAICompatibleClient(
            LLMConfig(
                model=resolved_model,
                base_url=base_url,
                api_key=api_key,
                use_show_context=use_show_context,
            )
        )
    raise ValueError(f"Unsupported provider: {provider}")
