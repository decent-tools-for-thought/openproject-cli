#!/usr/bin/env python3

"""Compatibility exports for the OpenProject CLI library package."""

from __future__ import annotations

from .auth import build_auth_header, load_token, resolve_auth_settings
from .commands import (
    add_common_auth_args,
    add_write_safety_args,
    cmd_login,
    cmd_me,
    cmd_projects,
    cmd_request,
    cmd_work_packages,
    maybe_add_wp_fields,
    maybe_add_wp_links,
)
from .config import (
    config_path,
    default_config_path,
    load_saved_config,
    require_base_url,
    save_config,
)
from .parser import build_parser, main
from .rendering import print_output
from .transport import (
    READ_ONLY_METHODS,
    build_url,
    confirm_write,
    maybe_parse_json,
    parse_body,
    request,
)

__all__ = [
    "READ_ONLY_METHODS",
    "add_common_auth_args",
    "add_write_safety_args",
    "build_auth_header",
    "build_parser",
    "build_url",
    "cmd_login",
    "cmd_me",
    "cmd_projects",
    "cmd_request",
    "cmd_work_packages",
    "config_path",
    "confirm_write",
    "default_config_path",
    "load_saved_config",
    "load_token",
    "main",
    "maybe_add_wp_fields",
    "maybe_add_wp_links",
    "maybe_parse_json",
    "parse_body",
    "print_output",
    "request",
    "require_base_url",
    "resolve_auth_settings",
    "save_config",
]
