from __future__ import annotations

import argparse
import base64
import os
from pathlib import Path
from typing import Any

from .config import load_saved_config, require_base_url


def load_token(
    token_arg: str | None,
    token_file_arg: str | None,
    saved_config: dict[str, Any] | None = None,
) -> str:
    if token_arg:
        return token_arg.strip()

    env_token = os.getenv("OP_API_TOKEN")
    if env_token:
        return env_token.strip()

    candidate_files: list[Path] = []
    if token_file_arg:
        candidate_files.append(Path(token_file_arg).expanduser())

    if not token_file_arg:
        config_token = (saved_config or {}).get("token")
        if isinstance(config_token, str) and config_token.strip():
            return config_token.strip()

    for file_path in candidate_files:
        if not file_path.exists():
            continue
        content = file_path.read_text(encoding="utf-8").strip()
        if not content:
            continue

        # Support either raw token or KEY=VALUE format.
        if "=" in content and not content.startswith("opapi-"):
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if key.strip() in {"OP_API_TOKEN", "OPENPROJECT_API_TOKEN", "API_TOKEN", "TOKEN"}:
                    return value.strip().strip('"').strip("'")

        return content

    raise SystemExit(
        "No API token found. Set OP_API_TOKEN, pass --token, provide --token-file, or run login."
    )


def resolve_auth_settings(args: argparse.Namespace) -> tuple[str, str, str, str]:
    saved = load_saved_config()
    base_url = require_base_url(args.base_url, saved)
    auth_mode = args.auth_mode or os.getenv("OP_AUTH_MODE") or saved.get("auth_mode") or "auto"
    username = args.username or os.getenv("OP_USERNAME") or saved.get("username") or "apikey"
    token = load_token(args.token, args.token_file, saved)
    return base_url, auth_mode, username, token


def build_auth_header(auth_mode: str, token: str, username: str | None) -> str:
    if auth_mode == "auto":
        # OpenProject API tokens usually have an opapi- prefix and work as Bearer.
        # Other token formats commonly work via Basic auth with user 'apikey'.
        auth_mode = "bearer" if token.startswith("opapi-") else "basic"

    if auth_mode == "bearer":
        return f"Bearer {token}"

    user = username or os.getenv("OP_USERNAME") or "apikey"
    basic = base64.b64encode(f"{user}:{token}".encode("utf-8")).decode("ascii")
    return f"Basic {basic}"
