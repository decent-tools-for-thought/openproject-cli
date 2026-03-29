from __future__ import annotations

import argparse
import urllib.parse
from pathlib import Path
from unittest.mock import patch

import pytest

from openproject_cli.attachment_commands import cmd_attachments
from openproject_cli.commands import cmd_projects, cmd_work_packages


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


def test_project_work_packages_merges_structured_filters() -> None:
    args = argparse.Namespace(
        subcommand="work-packages",
        project_id=7,
        assignee_id=8,
        responsible_id=None,
        status_id=3,
        type_id=None,
        priority_id=None,
        page_size=10,
        offset=1,
        filters=None,
        sort_by=None,
        timeout=30,
        output="json",
        headers=False,
        base_url="https://example.test",
        auth_mode="auto",
        username="apikey",
        token="opapi-token",
        token_file=None,
        yes=False,
        allow_write=False,
    )

    with patch("openproject_cli.commands.request", return_value=(200, {}, "{}")) as request_mock:
        assert cmd_projects(args) == 0

    url = request_mock.call_args.args[1]
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    filters = urllib.parse.unquote(query["filters"][0])
    assert parsed.path == "/api/v3/work_packages"
    assert '"project"' in filters
    assert '"assignee"' in filters
    assert '"status"' in filters


def test_work_package_comment_uses_activities_endpoint() -> None:
    args = argparse.Namespace(
        subcommand="comment",
        work_package_id=55,
        body='{"comment":{"raw":"hello"}}',
        timeout=30,
        output="json",
        headers=False,
        base_url="https://example.test",
        auth_mode="auto",
        username="apikey",
        token="opapi-token",
        token_file=None,
        yes=True,
        allow_write=True,
    )

    with patch("openproject_cli.commands.request", return_value=(201, {}, "{}")) as request_mock:
        assert cmd_work_packages(args) == 0

    assert request_mock.call_args.args[0] == "POST"
    assert request_mock.call_args.args[1].endswith("/api/v3/work_packages/55/activities")


def test_attachment_upload_targets_work_package_and_verifies(tmp_path: Path) -> None:
    pdf_path = tmp_path / "example.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    args = argparse.Namespace(
        subcommand="upload",
        container_type="work-package",
        container_id=803,
        path=str(pdf_path),
        file_name=None,
        description="Source PDF",
        content_type="application/pdf",
        verify=True,
        timeout=30,
        output="json",
        headers=False,
        base_url="https://example.test",
        auth_mode="auto",
        username="apikey",
        token="opapi-token",
        token_file=None,
        yes=True,
        allow_write=True,
    )

    with patch(
        "openproject_cli.attachment_commands.request_bytes",
        side_effect=[
            (201, {}, '{"id":97,"fileName":"example.pdf"}'),
            (200, {}, '{"_embedded":{"elements":[{"id":97}]}}'),
        ],
    ) as request_mock:
        assert cmd_attachments(args) == 0

    assert request_mock.call_args_list[0].args[0] == "POST"
    assert request_mock.call_args_list[0].args[1].endswith("/api/v3/work_packages/803/attachments")
    assert request_mock.call_args_list[1].args[0] == "GET"
    assert request_mock.call_args_list[1].args[1].endswith("/api/v3/work_packages/803/attachments")


def test_work_package_attach_file_uses_attachment_upload(tmp_path: Path) -> None:
    pdf_path = tmp_path / "example.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    args = argparse.Namespace(
        subcommand="attach-file",
        work_package_id=803,
        path=str(pdf_path),
        file_name=None,
        description=None,
        content_type=None,
        verify=False,
        timeout=30,
        output="json",
        headers=False,
        base_url="https://example.test",
        auth_mode="auto",
        username="apikey",
        token="opapi-token",
        token_file=None,
        yes=True,
        allow_write=True,
    )

    with patch(
        "openproject_cli.attachment_commands.request_bytes",
        return_value=(201, {}, '{"id":99,"fileName":"example.pdf"}'),
    ) as request_mock:
        assert cmd_work_packages(args) == 0

    assert request_mock.call_args.args[0] == "POST"
    assert request_mock.call_args.args[1].endswith("/api/v3/work_packages/803/attachments")
