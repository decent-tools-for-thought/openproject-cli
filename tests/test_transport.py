from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from openproject_cli.transport import build_url, confirm_write, maybe_parse_json, parse_body


def test_build_url_prefixes_api_v3_and_encodes_query() -> None:
    url = build_url(
        "https://openproject.example",
        "/projects",
        ["pageSize=5", "filters=" + json.dumps([{"active": {"operator": "=", "values": ["t"]}}])],
    )

    assert url.startswith("https://openproject.example/api/v3/projects?")
    assert "pageSize=5" in url
    assert "filters=%5B%7B%22active%22" in url


def test_build_url_accepts_explicit_api_path() -> None:
    assert build_url("https://openproject.example/", "/api/v3/projects/1", []) == (
        "https://openproject.example/api/v3/projects/1"
    )


def test_build_url_rejects_invalid_query() -> None:
    with pytest.raises(SystemExit, match="Invalid --query value"):
        build_url("https://openproject.example", "/projects", ["pageSize"])


def test_confirm_write_allows_read_only_methods_without_flags() -> None:
    confirm_write("GET", "https://openproject.example/api/v3/projects", False, False)


def test_confirm_write_requires_allow_write_flag() -> None:
    with pytest.raises(SystemExit, match="Add --allow-write"):
        confirm_write("PATCH", "https://openproject.example/api/v3/work_packages/1", True, False)


def test_confirm_write_prompts_and_cancels_without_yes_confirmation() -> None:
    with patch("builtins.input", return_value="no"):
        with pytest.raises(SystemExit, match="Write request cancelled."):
            confirm_write(
                "DELETE",
                "https://openproject.example/api/v3/work_packages/1",
                False,
                True,
            )


def test_maybe_parse_json_preserves_plain_text() -> None:
    assert maybe_parse_json("plain text") == "plain text"


def test_parse_body_rejects_invalid_json() -> None:
    with pytest.raises(SystemExit, match="Invalid JSON passed to --body"):
        parse_body("{not json}")
