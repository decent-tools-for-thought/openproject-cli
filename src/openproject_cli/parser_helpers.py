from __future__ import annotations

import argparse

from .commands import (
    add_collection_args,
    add_common_auth_args,
    add_json_body_arg,
    add_write_safety_args,
    perform_endpoint_request,
)


def add_endpoint_subcommand(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    name: str,
    *,
    help_text: str,
    method: str,
    path: str,
    auth: bool = True,
    collection: bool = False,
    body: bool = False,
    write: bool = False,
    positional_id: tuple[str, str] | None = None,
) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(name, help=help_text)
    if auth:
        add_common_auth_args(parser)
    if positional_id is not None:
        parser.add_argument(positional_id[0], type=int, help=positional_id[1])
    if collection:
        add_collection_args(parser)
    parser.add_argument(
        "--query",
        action="append",
        default=[],
        help="Additional query parameter key=value (repeatable)",
    )
    if body:
        add_json_body_arg(parser, "JSON object payload")
    if write:
        add_write_safety_args(parser)
    parser.set_defaults(
        func=perform_endpoint_request,
        http_method=method,
        api_path=path,
        is_collection=collection,
    )
    return parser


def add_standard_resource(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    name: str,
    *,
    path: str,
    help_text: str,
    allow_create: bool = False,
    allow_update: bool = False,
    allow_delete: bool = False,
    current_path: str | None = None,
) -> None:
    root = subparsers.add_parser(name, help=help_text)
    add_common_auth_args(root)
    root.set_defaults(command_parser=root)
    resource_sub = root.add_subparsers(dest="subcommand")

    list_parser = resource_sub.add_parser("list", help=f"List {name}")
    add_common_auth_args(list_parser)
    add_collection_args(list_parser)
    list_parser.add_argument(
        "--query",
        action="append",
        default=[],
        help="Additional query parameter key=value (repeatable)",
    )
    list_parser.set_defaults(
        func=perform_endpoint_request,
        http_method="GET",
        api_path=path,
        is_collection=True,
    )

    get_parser = resource_sub.add_parser("get", help=f"Get one {name.rstrip('s')}")
    add_common_auth_args(get_parser)
    get_parser.add_argument("resource_id", type=int)
    get_parser.add_argument(
        "--query",
        action="append",
        default=[],
        help="Additional query parameter key=value (repeatable)",
    )
    get_parser.set_defaults(
        func=perform_endpoint_request,
        http_method="GET",
        api_path=f"{path}/{{resource_id}}",
        is_collection=False,
    )

    if current_path is not None:
        current_parser = resource_sub.add_parser("current", help="Show the current resource")
        add_common_auth_args(current_parser)
        current_parser.add_argument(
            "--query",
            action="append",
            default=[],
            help="Additional query parameter key=value (repeatable)",
        )
        current_parser.set_defaults(
            func=perform_endpoint_request,
            http_method="GET",
            api_path=current_path,
            is_collection=False,
        )

    if allow_create:
        create_parser = resource_sub.add_parser("create", help=f"Create a {name.rstrip('s')}")
        add_common_auth_args(create_parser)
        add_json_body_arg(create_parser, "JSON object payload")
        add_write_safety_args(create_parser)
        create_parser.set_defaults(
            func=perform_endpoint_request,
            http_method="POST",
            api_path=path,
            is_collection=False,
        )

    if allow_update:
        update_parser = resource_sub.add_parser("update", help=f"Update a {name.rstrip('s')}")
        add_common_auth_args(update_parser)
        update_parser.add_argument("resource_id", type=int)
        add_json_body_arg(update_parser, "JSON object payload")
        add_write_safety_args(update_parser)
        update_parser.set_defaults(
            func=perform_endpoint_request,
            http_method="PATCH",
            api_path=f"{path}/{{resource_id}}",
            is_collection=False,
        )

    if allow_delete:
        delete_parser = resource_sub.add_parser("delete", help=f"Delete a {name.rstrip('s')}")
        add_common_auth_args(delete_parser)
        delete_parser.add_argument("resource_id", type=int)
        add_write_safety_args(delete_parser)
        delete_parser.set_defaults(
            func=perform_endpoint_request,
            http_method="DELETE",
            api_path=f"{path}/{{resource_id}}",
            is_collection=False,
        )
