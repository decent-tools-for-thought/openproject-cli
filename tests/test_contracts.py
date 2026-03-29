from __future__ import annotations

import urllib.parse
from unittest.mock import patch

import pytest

from openproject_cli.parser import main


def test_bare_invocation_prints_help_and_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    captured = capsys.readouterr()
    assert "OpenProject API v3 CLI with comprehensive resource commands" in captured.out


def test_subtree_help_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["users"]) == 0
    captured = capsys.readouterr()
    assert "usage: openproject-cli users" in captured.out
    assert "{list,get,current,create,update,delete}" in captured.out


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


def test_standard_resource_list_builds_collection_query() -> None:
    with patch("openproject_cli.commands.request", return_value=(200, {}, "{}")) as request_mock:
        assert (
            main(
                [
                    "users",
                    "list",
                    "--base-url",
                    "https://example.test",
                    "--token",
                    "opapi-token",
                    "--page-size",
                    "7",
                    "--offset",
                    "2",
                    "--filters",
                    '[{"status":{"operator":"=","values":["active"]}}]',
                    "--sort-by",
                    '[["id","desc"]]',
                ]
            )
            == 0
        )

    url = request_mock.call_args.args[1]
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    assert parsed.path == "/api/v3/users"
    assert query["pageSize"] == ["7"]
    assert query["offset"] == ["2"]
    assert "status" in urllib.parse.unquote(query["filters"][0])
    assert "id" in urllib.parse.unquote(query["sortBy"][0])
