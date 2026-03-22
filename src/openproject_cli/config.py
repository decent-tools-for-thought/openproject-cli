from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def default_config_path() -> Path:
    config_home = os.getenv("XDG_CONFIG_HOME")
    base_dir = Path(config_home).expanduser() if config_home else Path.home() / ".config"
    return base_dir / "openproject-cli" / "config.json"


def config_path() -> Path:
    raw = os.getenv("OPENPROJECT_CLI_CONFIG")
    return Path(raw).expanduser() if raw else default_config_path()


def load_saved_config() -> dict[str, Any]:
    path = config_path()
    if not path.exists():
        return {}

    try:
        content = path.read_text(encoding="utf-8")
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_config(config: dict[str, Any]) -> Path:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Keep file access private as it stores API credentials.
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass

    path.write_text(json.dumps(config, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass

    return path


def require_base_url(explicit_base_url: str | None, saved: dict[str, Any]) -> str:
    base_url = explicit_base_url or os.getenv("OP_BASE_URL") or saved.get("base_url")
    if not base_url:
        raise SystemExit(
            "No base URL configured. Pass --base-url, set OP_BASE_URL, or run "
            "`openproject login --base-url <url>`."
        )
    return base_url
