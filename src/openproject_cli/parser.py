from __future__ import annotations

import argparse
from typing import Protocol, cast

from .commands import (
    add_common_auth_args,
    add_write_safety_args,
    cmd_login,
    cmd_me,
    cmd_projects,
    cmd_request,
    cmd_work_packages,
)


class ArgHandler(Protocol):
    def __call__(self, args: argparse.Namespace) -> int: ...


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="openproject-cli",
        description="OpenProject API v3 CLI (safe by default).",
    )
    subparsers = parser.add_subparsers(dest="command")

    me = subparsers.add_parser("me", help="Show current user")
    add_common_auth_args(me)
    me.set_defaults(func=cmd_me)

    login = subparsers.add_parser("login", help="Save OpenProject credentials for future commands")
    login.add_argument("--base-url", default=None)
    login.add_argument("--token")
    login.add_argument("--token-file", default=None)
    login.add_argument("--auth-mode", choices=["auto", "bearer", "basic"], default=None)
    login.add_argument("--username", default=None)
    login.add_argument("--timeout", type=int, default=30)
    login.add_argument(
        "--no-test",
        action="store_true",
        help="Skip credentials test against /users/me",
    )
    login.set_defaults(func=cmd_login)

    projects = subparsers.add_parser("projects", help="Project operations")
    add_common_auth_args(projects)
    projects_sub = projects.add_subparsers(dest="subcommand")

    p_list = projects_sub.add_parser("list", help="List projects")
    p_list.add_argument("--page-size", type=int, default=20)
    p_list.add_argument("--offset", type=int, default=1)
    p_list.add_argument(
        "--filters",
        help=(
            "Raw OpenProject filters JSON string, "
            'e.g. \'[{"active":{"operator":"=","values":["t"]}}]\'.'
        ),
    )

    p_get = projects_sub.add_parser("get", help="Get one project")
    p_get.add_argument("project_id")
    projects.set_defaults(func=cmd_projects)

    wp = subparsers.add_parser("work-packages", help="Work package operations")
    add_common_auth_args(wp)
    wp_sub = wp.add_subparsers(dest="subcommand")

    wp_list = wp_sub.add_parser("list", help="List work packages")
    wp_list.add_argument("--page-size", type=int, default=20)
    wp_list.add_argument("--offset", type=int, default=1)
    wp_list.add_argument("--project-id", type=int)
    wp_list.add_argument(
        "--filters",
        help="Raw OpenProject filters JSON string; overrides --project-id filter if also provided.",
    )

    wp_get = wp_sub.add_parser("get", help="Get one work package")
    wp_get.add_argument("work_package_id")

    wp_create = wp_sub.add_parser("create", help="Create a work package in a project")
    wp_create.add_argument("project_id", type=int)
    wp_create.add_argument("--subject", required=True)
    wp_create.add_argument("--description", help="Markdown description")
    wp_create.add_argument("--type-id", type=int)
    wp_create.add_argument("--status-id", type=int)
    wp_create.add_argument("--priority-id", type=int)
    wp_create.add_argument("--assignee-id", type=int)
    wp_create.add_argument("--responsible-id", type=int)
    wp_create.add_argument("--start-date", help="YYYY-MM-DD")
    wp_create.add_argument("--due-date", help="YYYY-MM-DD")
    wp_create.add_argument("--body", help="Additional JSON object payload (merged last)")
    add_write_safety_args(wp_create)

    wp_update = wp_sub.add_parser("update", help="Update a work package")
    wp_update.add_argument("work_package_id", type=int)
    wp_update.add_argument("--lock-version", type=int, help="Optional. Auto-fetched if omitted.")
    wp_update.add_argument("--subject")
    wp_update.add_argument("--description", help="Markdown description")
    wp_update.add_argument("--type-id", type=int)
    wp_update.add_argument("--status-id", type=int)
    wp_update.add_argument("--priority-id", type=int)
    wp_update.add_argument("--assignee-id", type=int)
    wp_update.add_argument("--responsible-id", type=int)
    wp_update.add_argument("--start-date", help="YYYY-MM-DD")
    wp_update.add_argument("--due-date", help="YYYY-MM-DD")
    wp_update.add_argument("--body", help="JSON object payload merged before explicit flags")
    add_write_safety_args(wp_update)

    wp_delete = wp_sub.add_parser("delete", help="Delete a work package")
    wp_delete.add_argument("work_package_id", type=int)
    wp_delete.add_argument(
        "--confirm-delete",
        help="Required with --yes. Must equal delete-<work_package_id>.",
    )
    add_write_safety_args(wp_delete)

    wp.set_defaults(func=cmd_work_packages)

    req = subparsers.add_parser("request", help="Generic API request")
    add_common_auth_args(req)
    req.add_argument("path", help="API path, e.g. '/projects' or '/api/v3/projects'")
    req.add_argument("--method", default="GET", help="HTTP method (default: GET)")
    req.add_argument(
        "--query",
        action="append",
        default=[],
        help="Query parameter key=value (repeatable)",
    )
    req.add_argument("--body", help="JSON payload for write requests")
    req.add_argument(
        "--allow-write",
        action="store_true",
        help="Allow POST/PUT/PATCH/DELETE methods",
    )
    req.add_argument(
        "--yes",
        action="store_true",
        help="Skip interactive write confirmation prompt",
    )
    req.set_defaults(func=cmd_request)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if args.command in {"projects", "work-packages"} and args.subcommand is None:
        next(
            action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
        ).choices[args.command].print_help()
        return 0
    handler = cast(ArgHandler, args.func)
    return handler(args)
