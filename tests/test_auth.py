from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

from openproject_cli.auth import build_auth_header, load_token, resolve_auth_settings


def make_args(**overrides: str | None) -> argparse.Namespace:
    defaults: dict[str, str | None] = {
        "base_url": None,
        "auth_mode": None,
        "username": None,
        "token": None,
        "token_file": None,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def test_load_token_prefers_explicit_argument(tmp_path: Path) -> None:
    token_file = tmp_path / "token.txt"
    token_file.write_text("file-token\n", encoding="utf-8")

    with patch.dict("os.environ", {"OP_API_TOKEN": "env-token"}, clear=False):
        token = load_token(" arg-token ", str(token_file), {"token": "saved-token"})

    assert token == "arg-token"


def test_load_token_prefers_environment_over_token_file_and_saved_config(tmp_path: Path) -> None:
    token_file = tmp_path / "token.txt"
    token_file.write_text("file-token\n", encoding="utf-8")

    with patch.dict("os.environ", {"OP_API_TOKEN": " env-token "}, clear=False):
        token = load_token(None, str(token_file), {"token": "saved-token"})

    assert token == "env-token"


def test_load_token_uses_saved_config_before_file_when_no_file_flag() -> None:
    with patch.dict("os.environ", {}, clear=True):
        token = load_token(None, None, {"token": " saved-token "})

    assert token == "saved-token"


def test_load_token_parses_key_value_token_file(tmp_path: Path) -> None:
    token_file = tmp_path / "token.env"
    token_file.write_text(
        "# comment\nOPENPROJECT_API_TOKEN='quoted-token'\nIGNORED=value\n",
        encoding="utf-8",
    )

    token = load_token(None, str(token_file), None)

    assert token == "quoted-token"


def test_load_token_returns_raw_file_contents_for_non_env_format(tmp_path: Path) -> None:
    token_file = tmp_path / "token.txt"
    token_file.write_text("raw-token\n", encoding="utf-8")

    token = load_token(None, str(token_file), None)

    assert token == "raw-token"


def test_resolve_auth_settings_uses_cli_env_and_saved_precedence() -> None:
    saved = {
        "base_url": "https://saved.example",
        "auth_mode": "basic",
        "username": "saved-user",
        "token": "saved-token",
    }
    args = make_args(base_url="https://cli.example", token="cli-token")

    with (
        patch("openproject_cli.auth.load_saved_config", return_value=saved),
        patch.dict(
            "os.environ",
            {"OP_AUTH_MODE": "bearer", "OP_USERNAME": "env-user"},
            clear=False,
        ),
    ):
        resolved = resolve_auth_settings(args)

    assert resolved == ("https://cli.example", "bearer", "env-user", "cli-token")


def test_build_auth_header_auto_uses_bearer_for_opapi_token() -> None:
    assert build_auth_header("auto", "opapi-abc123", None) == "Bearer opapi-abc123"


def test_build_auth_header_basic_uses_username_fallback() -> None:
    with patch.dict("os.environ", {}, clear=True):
        header = build_auth_header("basic", "secret", None)

    assert header == "Basic YXBpa2V5OnNlY3JldA=="


def test_resolve_auth_settings_requires_base_url() -> None:
    args = make_args(token="cli-token")

    with (
        patch("openproject_cli.auth.load_saved_config", return_value={}),
        patch.dict(
            "os.environ",
            {},
            clear=True,
        ),
    ):
        with pytest.raises(SystemExit, match="No base URL configured"):
            resolve_auth_settings(args)
