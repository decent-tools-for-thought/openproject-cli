from __future__ import annotations

import argparse
from unittest.mock import patch

import pytest

from openproject_cli.commands import cmd_work_packages


def test_delete_requires_confirm_token_when_yes_is_used() -> None:
    args = argparse.Namespace(
        subcommand="delete",
        work_package_id=123,
        yes=True,
        allow_write=True,
        confirm_delete=None,
        timeout=30,
        output="json",
        headers=False,
        base_url="https://example.test",
        auth_mode="auto",
        username="apikey",
        token="opapi-token",
        token_file=None,
    )

    with pytest.raises(SystemExit, match="Delete requires --confirm-delete delete-123"):
        cmd_work_packages(args)


def test_delete_cancels_when_delete_token_confirmation_fails() -> None:
    args = argparse.Namespace(
        subcommand="delete",
        work_package_id=123,
        yes=False,
        allow_write=True,
        confirm_delete=None,
        timeout=30,
        output="json",
        headers=False,
        base_url="https://example.test",
        auth_mode="auto",
        username="apikey",
        token="opapi-token",
        token_file=None,
    )

    with (
        patch("builtins.input", side_effect=["yes", "nope"]),
        pytest.raises(SystemExit, match="Delete request cancelled."),
    ):
        cmd_work_packages(args)
