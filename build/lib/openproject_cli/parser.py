from __future__ import annotations

import argparse
from typing import Protocol, cast

from .attachment_commands import cmd_attachments
from .commands import (
    add_collection_args,
    add_common_auth_args,
    add_json_body_arg,
    add_write_safety_args,
    cmd_login,
    cmd_me,
    cmd_projects,
    cmd_request,
    cmd_work_packages,
)
from .parser_helpers import add_endpoint_subcommand, add_standard_resource


class ArgHandler(Protocol):
    def __call__(self, args: argparse.Namespace) -> int: ...


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="openproject-cli",
        description="OpenProject API v3 CLI with comprehensive resource commands.",
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

    add_standard_resource(
        subparsers,
        "activities",
        path="/activities",
        help_text="Activity endpoints",
    )
    attachments = subparsers.add_parser("attachments", help="Attachment upload and lookup")
    add_common_auth_args(attachments)
    attachments_sub = attachments.add_subparsers(dest="subcommand")

    a_get = attachments_sub.add_parser("get", help="Get one attachment")
    add_common_auth_args(a_get)
    a_get.add_argument("attachment_id", type=int)
    a_get.set_defaults(func=cmd_attachments)

    a_delete = attachments_sub.add_parser("delete", help="Delete one attachment")
    add_common_auth_args(a_delete)
    a_delete.add_argument("attachment_id", type=int)
    add_write_safety_args(a_delete)
    a_delete.set_defaults(func=cmd_attachments)

    a_create = attachments_sub.add_parser("create", help="Upload a containerless attachment")
    add_common_auth_args(a_create)
    a_create.add_argument("path", help="Local file to upload")
    a_create.add_argument("--file-name", help="Override metadata fileName")
    a_create.add_argument("--description", help="Attachment description")
    a_create.add_argument("--content-type", help="Override detected MIME type")
    add_write_safety_args(a_create)
    a_create.set_defaults(func=cmd_attachments, verify=False)

    for subcommand_name, help_text in (
        ("list", "List attachments for a container"),
        ("upload", "Upload an attachment to a container"),
    ):
        parser_obj = attachments_sub.add_parser(subcommand_name, help=help_text)
        add_common_auth_args(parser_obj)
        parser_obj.add_argument(
            "container_type",
            choices=["activity", "meeting", "post", "wiki-page", "work-package"],
        )
        parser_obj.add_argument("container_id", type=int)
        if subcommand_name == "upload":
            parser_obj.add_argument("path", help="Local file to upload")
            parser_obj.add_argument("--file-name", help="Override metadata fileName")
            parser_obj.add_argument("--description", help="Attachment description")
            parser_obj.add_argument("--content-type", help="Override detected MIME type")
            parser_obj.add_argument(
                "--verify",
                action="store_true",
                help="Read back the container attachment list after upload",
            )
            add_write_safety_args(parser_obj)
        parser_obj.set_defaults(func=cmd_attachments)

    attachments.set_defaults(command_parser=attachments)

    add_standard_resource(
        subparsers,
        "categories",
        path="/categories",
        help_text="Category endpoints",
    )
    add_standard_resource(
        subparsers,
        "memberships",
        path="/memberships",
        help_text="Membership endpoints",
        allow_create=True,
        allow_update=True,
        allow_delete=True,
    )
    add_standard_resource(
        subparsers,
        "priorities",
        path="/priorities",
        help_text="Priority endpoints",
    )
    add_standard_resource(
        subparsers,
        "queries",
        path="/queries",
        help_text="Query endpoints",
        allow_create=True,
        allow_update=True,
        allow_delete=True,
    )
    add_standard_resource(
        subparsers,
        "relations",
        path="/relations",
        help_text="Relation endpoints",
        allow_create=True,
        allow_update=True,
        allow_delete=True,
    )
    add_standard_resource(subparsers, "roles", path="/roles", help_text="Role endpoints")
    add_standard_resource(subparsers, "statuses", path="/statuses", help_text="Status endpoints")
    add_standard_resource(
        subparsers,
        "time-entries",
        path="/time_entries",
        help_text="Time entry endpoints",
        allow_create=True,
        allow_update=True,
        allow_delete=True,
    )
    add_standard_resource(
        subparsers,
        "time-entry-activities",
        path="/time_entries/activities",
        help_text="Time entry activity endpoints",
    )
    add_standard_resource(subparsers, "types", path="/types", help_text="Type endpoints")
    add_standard_resource(
        subparsers,
        "users",
        path="/users",
        help_text="User endpoints",
        allow_create=True,
        allow_update=True,
        allow_delete=True,
        current_path="/users/me",
    )
    add_standard_resource(subparsers, "versions", path="/versions", help_text="Version endpoints")

    root = subparsers.add_parser("root", help="Show API root document")
    add_common_auth_args(root)
    root_sub = root.add_subparsers(dest="subcommand")
    add_endpoint_subcommand(
        root_sub,
        "show",
        help_text="Show /api/v3 root document",
        method="GET",
        path="/api/v3",
        auth=True,
    )
    root.set_defaults(command_parser=root)

    config = subparsers.add_parser("configuration", help="Show global configuration")
    add_common_auth_args(config)
    config_sub = config.add_subparsers(dest="subcommand")
    add_endpoint_subcommand(
        config_sub,
        "show",
        help_text="Show global configuration",
        method="GET",
        path="/configuration",
        auth=True,
    )
    config.set_defaults(command_parser=config)

    prefs = subparsers.add_parser("user-preferences", help="Show current user preferences")
    add_common_auth_args(prefs)
    prefs_sub = prefs.add_subparsers(dest="subcommand")
    add_endpoint_subcommand(
        prefs_sub,
        "show",
        help_text="Show current user preferences",
        method="GET",
        path="/my_preferences",
        auth=True,
    )
    prefs.set_defaults(command_parser=prefs)

    projects = subparsers.add_parser("projects", help="Project and workspace operations")
    add_common_auth_args(projects)
    projects_sub = projects.add_subparsers(dest="subcommand")

    p_list = projects_sub.add_parser("list", help="List projects")
    add_common_auth_args(p_list)
    add_collection_args(p_list)
    p_list.add_argument("--active-only", action="store_true", help="Only active projects")
    p_list.set_defaults(func=cmd_projects)

    p_get = projects_sub.add_parser("get", help="Get one project")
    add_common_auth_args(p_get)
    p_get.add_argument("project_id", type=int)
    p_get.set_defaults(func=cmd_projects)

    p_create = projects_sub.add_parser("create", help="Create a project")
    add_common_auth_args(p_create)
    add_json_body_arg(p_create, "JSON object payload")
    add_write_safety_args(p_create)
    p_create.set_defaults(func=cmd_projects)

    p_update = projects_sub.add_parser("update", help="Update a project")
    add_common_auth_args(p_update)
    p_update.add_argument("project_id", type=int)
    add_json_body_arg(p_update, "JSON object payload")
    add_write_safety_args(p_update)
    p_update.set_defaults(func=cmd_projects)

    p_delete = projects_sub.add_parser("delete", help="Delete a project")
    add_common_auth_args(p_delete)
    p_delete.add_argument("project_id", type=int)
    add_write_safety_args(p_delete)
    p_delete.set_defaults(func=cmd_projects)

    p_status = projects_sub.add_parser("status", help="Get a project status by code")
    add_common_auth_args(p_status)
    p_status.add_argument("status_id")
    p_status.set_defaults(func=cmd_projects)

    p_config = projects_sub.add_parser("configuration", help="Show one project's configuration")
    add_common_auth_args(p_config)
    p_config.add_argument("project_id", type=int)
    p_config.set_defaults(func=cmd_projects)

    p_copy = projects_sub.add_parser("copy", help="Trigger a project copy")
    add_common_auth_args(p_copy)
    p_copy.add_argument("project_id", type=int)
    p_copy.add_argument("--body", help="Optional JSON object payload")
    add_write_safety_args(p_copy)
    p_copy.set_defaults(func=cmd_projects)

    for scoped_name, help_text in (
        ("categories", "List categories of a project"),
        ("memberships", "List memberships of a project"),
        ("queries", "List queries of a project"),
        ("types", "List types of a project"),
        ("versions", "List versions of a project"),
    ):
        scoped = projects_sub.add_parser(scoped_name, help=help_text)
        add_common_auth_args(scoped)
        scoped.add_argument("project_id", type=int)
        add_collection_args(scoped)
        scoped.set_defaults(func=cmd_projects)

    p_wps = projects_sub.add_parser("work-packages", help="List work packages of a project")
    add_common_auth_args(p_wps)
    p_wps.add_argument("project_id", type=int)
    add_collection_args(p_wps)
    p_wps.add_argument("--assignee-id", type=int)
    p_wps.add_argument("--responsible-id", type=int)
    p_wps.add_argument("--status-id", type=int)
    p_wps.add_argument("--type-id", type=int)
    p_wps.add_argument("--priority-id", type=int)
    p_wps.set_defaults(func=cmd_projects)

    projects.set_defaults(command_parser=projects)

    wp = subparsers.add_parser("work-packages", help="Work package operations")
    add_common_auth_args(wp)
    wp_sub = wp.add_subparsers(dest="subcommand")

    wp_list = wp_sub.add_parser("list", help="List work packages")
    add_common_auth_args(wp_list)
    add_collection_args(wp_list)
    wp_list.add_argument("--project-id", type=int)
    wp_list.add_argument("--assignee-id", type=int)
    wp_list.add_argument("--responsible-id", type=int)
    wp_list.add_argument("--status-id", type=int)
    wp_list.add_argument("--type-id", type=int)
    wp_list.add_argument("--priority-id", type=int)
    wp_list.set_defaults(func=cmd_work_packages)

    wp_get = wp_sub.add_parser("get", help="Get one work package")
    add_common_auth_args(wp_get)
    wp_get.add_argument("work_package_id", type=int)
    wp_get.set_defaults(func=cmd_work_packages)

    wp_create = wp_sub.add_parser("create", help="Create a work package in a project")
    add_common_auth_args(wp_create)
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
    wp_create.set_defaults(func=cmd_work_packages)

    wp_update = wp_sub.add_parser("update", help="Update a work package")
    add_common_auth_args(wp_update)
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
    wp_update.set_defaults(func=cmd_work_packages)

    wp_delete = wp_sub.add_parser("delete", help="Delete a work package")
    add_common_auth_args(wp_delete)
    wp_delete.add_argument("work_package_id", type=int)
    wp_delete.add_argument(
        "--confirm-delete",
        help="Required with --yes. Must equal delete-<work_package_id>.",
    )
    add_write_safety_args(wp_delete)
    wp_delete.set_defaults(func=cmd_work_packages)

    for scoped_name, help_text in (
        ("activities", "List work package activities"),
        ("available-assignees", "List available assignees"),
        ("available-projects", "List available projects"),
        ("available-watchers", "List available watchers"),
        ("relation-candidates", "List available relation candidates"),
    ):
        scoped = wp_sub.add_parser(scoped_name, help=help_text)
        add_common_auth_args(scoped)
        scoped.add_argument("work_package_id", type=int)
        add_collection_args(scoped)
        scoped.set_defaults(func=cmd_work_packages)

    wp_comment = wp_sub.add_parser("comment", help="Create a work package activity comment")
    add_common_auth_args(wp_comment)
    wp_comment.add_argument("work_package_id", type=int)
    add_json_body_arg(wp_comment, "JSON object payload")
    add_write_safety_args(wp_comment)
    wp_comment.set_defaults(func=cmd_work_packages)

    wp_attachments = wp_sub.add_parser("attachments", help="List attachments on a work package")
    add_common_auth_args(wp_attachments)
    wp_attachments.add_argument("work_package_id", type=int)
    wp_attachments.set_defaults(func=cmd_work_packages)

    wp_attach_file = wp_sub.add_parser("attach-file", help="Upload a file to a work package")
    add_common_auth_args(wp_attach_file)
    wp_attach_file.add_argument("work_package_id", type=int)
    wp_attach_file.add_argument("path", help="Local file to upload")
    wp_attach_file.add_argument("--file-name", help="Override metadata fileName")
    wp_attach_file.add_argument("--description", help="Attachment description")
    wp_attach_file.add_argument("--content-type", help="Override detected MIME type")
    wp_attach_file.add_argument(
        "--verify",
        action="store_true",
        help="Read back the work package attachment list after upload",
    )
    add_write_safety_args(wp_attach_file)
    wp_attach_file.set_defaults(func=cmd_work_packages)

    wp.set_defaults(command_parser=wp)

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
    add_write_safety_args(req)
    req.set_defaults(func=cmd_request)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if getattr(args, "subcommand", None) is None and hasattr(args, "command_parser"):
        args.command_parser.print_help()
        return 0
    handler = cast(ArgHandler, args.func)
    return handler(args)
