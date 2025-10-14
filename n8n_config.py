"""Utility helpers for persisting n8n integration settings.

The configuration is stored in a small YAML file (n8n_config.yaml) in the
project root so that both the FastAPI server and auxiliary scripts can reuse
it.  Only a handful of fields are tracked: base URL, webhook path and optional
API key.  All fields are stored as strings and defaults are empty strings to
make template rendering easier.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict

import yaml

DEFAULT_CONFIG: Dict[str, str] = {
    "base_url": "",
    "webhook_path": "",
    "api_key": "",
}

CONFIG_PATH = Path("n8n_config.yaml")


def load_n8n_config(path: Path = CONFIG_PATH) -> Dict[str, str]:
    """Return the stored n8n configuration or defaults when missing."""
    if not path.exists():
        return DEFAULT_CONFIG.copy()

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    config = DEFAULT_CONFIG.copy()
    for key, value in data.items():
        if key in config and value is not None:
            config[key] = str(value)
    return config


def save_n8n_config(config: Dict[str, str], path: Path = CONFIG_PATH) -> None:
    """Persist the provided n8n configuration to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    to_store = DEFAULT_CONFIG.copy()
    for key in to_store:
        if key in config and config[key] is not None:
            to_store[key] = str(config[key]).strip()
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(to_store, f, allow_unicode=True, sort_keys=True)
