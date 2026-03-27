from __future__ import annotations

import pytest

from openproject_cli.rendering import print_output


def test_print_output_renders_json_body(capsys: pytest.CaptureFixture[str]) -> None:
    print_output(200, {}, '{"name":"demo"}', "json", False)

    captured = capsys.readouterr()
    assert '"name": "demo"' in captured.out


def test_print_output_renders_raw_body_with_headers(capsys: pytest.CaptureFixture[str]) -> None:
    print_output(204, {"X-Test": "yes"}, "plain text", "raw", True)

    captured = capsys.readouterr()
    assert "HTTP 204" in captured.out
    assert "X-Test: yes" in captured.out
    assert "plain text" in captured.out
