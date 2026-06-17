"""Config loader with ${ENV_VAR} interpolation."""

from __future__ import annotations

import os
import re
from pathlib import Path

import yaml


def load_config(path: str) -> dict:
    """Load a YAML config file and expand ${VAR} references from environment."""
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {path}\n"
            "Hint: copy config/config.example.yaml to config/config.yaml"
        )

    raw = config_path.read_text(encoding="utf-8")

    def _replace_env(match: re.Match[str]) -> str:
        var_name = match.group(1)
        value = os.environ.get(var_name)
        if value is None:
            raise ValueError(
                f"Environment variable '{var_name}' is not set. "
                "This variable is required by the config file."
            )
        return value

    lines: list[str] = []
    for line in raw.split("\n"):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            lines.append(line)
            continue
        lines.append(re.sub(r"\$\{(\w+)\}", _replace_env, line))

    config = yaml.safe_load("\n".join(lines)) or {}
    _validate_config(config)
    return config


def _validate_config(config: dict) -> None:
    """Basic sanity checks on the config structure."""
    required_sections = ["llm", "feishu", "output"]
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Config missing required section: '{section}'")

    if "model" not in config["llm"]:
        raise ValueError("config.llm.model is required")
    if "base_url" not in config["llm"]:
        raise ValueError("config.llm.base_url is required")
    if "api_key" not in config["llm"]:
        raise ValueError("config.llm.api_key is required")

    if "wiki_space_id" not in config["feishu"]:
        raise ValueError("config.feishu.wiki_space_id is required")
    if "app_id" not in config["feishu"] or "app_secret" not in config["feishu"]:
        raise ValueError("config.feishu.app_id and config.feishu.app_secret are required")
