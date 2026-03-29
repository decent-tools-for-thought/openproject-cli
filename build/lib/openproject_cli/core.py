#!/usr/bin/env python3

"""Compatibility exports for the OpenProject CLI library package."""

from __future__ import annotations

from .attachment_commands import cmd_attachments
from .auth import build_auth_header, load_token, resolve_auth_settings
from .commands import (
    add_collection_args,
    add_common_auth_args,
    add_json_body_arg,
    add_write_safety_args,
    build_collection_query,
    cmd_login,
    cmd_me,
    cmd_projects,
    cmd_request,
    cmd_work_packages,
    maybe_add_wp_fields,
    maybe_add_wp_links,
    perform_endpoint_request,
)
from .config import (
    config_path,
    default_config_path,
    load_saved_config,
    require_base_url,
    save_config,
)
from .parser import build_parser, main
from .parser_helpers import add_endpoint_subcommand, add_standard_resource
from .rendering import print_output
from .transport import (
    READ_ONLY_METHODS,
    build_multipart_form_data,
    build_url,
    confirm_write,
    maybe_parse_json,
    parse_body,
    request,
    request_bytes,
)

__all__ = [
    "READ_ONLY_METHODS",
    "add_collection_args",
    "add_common_auth_args",
    "add_endpoint_subcommand",
    "add_json_body_arg",
    "add_standard_resource",
    "add_write_safety_args",
    "build_auth_header",
    "build_multipart_form_data",
    "build_collection_query",
    "build_parser",
    "build_url",
    "cmd_attachments",
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
    "perform_endpoint_request",
    "print_output",
    "request",
    "request_bytes",
    "require_base_url",
    "resolve_auth_settings",
    "save_config",
]
