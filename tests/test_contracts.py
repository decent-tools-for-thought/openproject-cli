from __future__ import annotations

from unittest.mock import patch

import pytest

from openproject_cli.parser import main


def test_bare_invocation_prints_help_and_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    captured = capsys.readouterr()
    assert "OpenProject API v3 CLI" in captured.out


def test_subtree_help_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["projects"]) == 0
    captured = capsys.readouterr()
    assert "usage: openproject-cli projects" in captured.out
    assert "{list,get}" in captured.out


def test_usage_errors_return_argparse_exit_code() -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["work-packages", "create", "1"])

    assert excinfo.value.code == 2


def test_destructive_request_stays_gated_before_network_access() -> None:
    with patch("openproject_cli.commands.request") as request_mock:
        with pytest.raises(SystemExit, match="Refusing POST request"):
            main(
                [
                    "request",
                    "/work_packages",
                    "--method",
                    "POST",
                    "--base-url",
                    "https://example.test",
                    "--token",
                    "opapi-token",
                ]
            )

    request_mock.assert_not_called()
