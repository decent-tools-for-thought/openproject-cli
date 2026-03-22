from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from openproject_cli.config import config_path, default_config_path


def test_default_config_path_uses_xdg_config_home_when_set() -> None:
    with patch.dict("os.environ", {"XDG_CONFIG_HOME": "/tmp/xdg-config-home"}, clear=False):
        assert default_config_path() == Path("/tmp/xdg-config-home/openproject-cli/config.json")


def test_default_config_path_falls_back_to_home_config_dir() -> None:
    with patch.dict("os.environ", {}, clear=True):
        assert default_config_path() == Path.home() / ".config" / "openproject-cli" / "config.json"


def test_config_path_prefers_explicit_override() -> None:
    env = {
        "XDG_CONFIG_HOME": "/tmp/xdg-config-home",
        "OPENPROJECT_CLI_CONFIG": "~/custom-openproject-cli.json",
    }
    with patch.dict("os.environ", env, clear=False):
        assert config_path() == Path("~/custom-openproject-cli.json").expanduser()
