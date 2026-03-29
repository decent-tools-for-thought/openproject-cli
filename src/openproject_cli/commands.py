from __future__ import annotations

import argparse
import getpass
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .auth import build_auth_header, load_token, resolve_auth_settings
from .config import load_saved_config, save_config
from .rendering import print_output
from .transport import build_url, confirm_write, maybe_parse_json, parse_body, request


def add_write_safety_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--allow-write",
        action="store_true",
        help="Allow state-changing API requests",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip interactive write confirmation prompt",
    )


def add_common_auth_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--token")
    parser.add_argument("--token-file", default=None)
    parser.add_argument("--auth-mode", choices=["auto", "bearer", "basic"], default=None)
    parser.add_argument(
        "--username",
        default=None,
        help=(
            "Used only when --auth-mode basic "
            "(for API token basic auth, OpenProject recommends username 'apikey')."
        ),
    )
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--output", choices=["json", "raw"], default="json")
    parser.add_argument(
        "--headers",
        action="store_true",
        help="Include HTTP status and response headers",
    )


def add_collection_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--page-size", type=int, default=20)
    parser.add_argument("--offset", type=int, default=1)
    parser.add_argument(
        "--filters",
        help="Raw OpenProject filters JSON string.",
    )
    parser.add_argument(
        "--sort-by",
        help='Raw OpenProject sortBy JSON string, e.g. \'[["id","asc"]]\'.',
    )


def add_json_body_arg(parser: argparse.ArgumentParser, help_text: str) -> None:
    parser.add_argument("--body", required=True, help=help_text)


def auth_context(args: argparse.Namespace) -> tuple[str, str, int]:
    base_url, auth_mode, username, token = resolve_auth_settings(args)
    auth_header = build_auth_header(auth_mode, token, username)
    return base_url, auth_header, args.timeout


def render_response(
    args: argparse.Namespace,
    status: int,
    headers: dict[str, str],
    body: str,
) -> int:
    print_output(status, headers, body, args.output, args.headers)
    return 0 if 200 <= status < 300 else 1


def parse_filter_list(raw_filters: str | None) -> list[dict[str, Any]]:
    if raw_filters is None:
        return []

    parsed = parse_body(raw_filters)
    if not isinstance(parsed, list):
        raise SystemExit("--filters must decode to a JSON array.")
    if not all(isinstance(item, dict) for item in parsed):
        raise SystemExit("--filters must be a JSON array of objects.")
    return parsed


def build_collection_query(
    args: argparse.Namespace,
    *,
    extra_filters: list[dict[str, Any]] | None = None,
) -> list[str]:
    query = [f"pageSize={args.page_size}", f"offset={args.offset}"]
    filters = list(extra_filters or [])
    filters.extend(parse_filter_list(getattr(args, "filters", None)))
    if filters:
        query.append(f"filters={json.dumps(filters)}")
    if getattr(args, "sort_by", None):
        query.append(f"sortBy={args.sort_by}")
    return query


def perform_request(
    args: argparse.Namespace,
    method: str,
    path: str,
    *,
    query: list[str] | None = None,
    body_obj: Any = None,
) -> int:
    base_url, auth_header, timeout = auth_context(args)
    url = build_url(base_url, path, query or [])
    confirm_write(method, url, getattr(args, "yes", False), getattr(args, "allow_write", False))
    status, headers, body = request(method, url, auth_header, body_obj, timeout)
    return render_response(args, status, headers, body)


def perform_endpoint_request(args: argparse.Namespace) -> int:
    path = args.api_path.format(**vars(args))
    method = args.http_method.upper()
    query = list(getattr(args, "query", []))
    if getattr(args, "is_collection", False):
        query = build_collection_query(args) + query
    body_obj = parse_body(args.body) if getattr(args, "body", None) is not None else None
    return perform_request(args, method, path, query=query, body_obj=body_obj)


def maybe_add_wp_links(payload: dict[str, Any], args: argparse.Namespace) -> None:
    links: dict[str, Any] = payload.get("_links", {})
    if args.type_id is not None:
        links["type"] = {"href": f"/api/v3/types/{args.type_id}"}
    if args.status_id is not None:
        links["status"] = {"href": f"/api/v3/statuses/{args.status_id}"}
    if args.priority_id is not None:
        links["priority"] = {"href": f"/api/v3/priorities/{args.priority_id}"}
    if args.assignee_id is not None:
        links["assignee"] = {"href": f"/api/v3/users/{args.assignee_id}"}
    if args.responsible_id is not None:
        links["responsible"] = {"href": f"/api/v3/users/{args.responsible_id}"}

    if links:
        payload["_links"] = links


def maybe_add_wp_fields(payload: dict[str, Any], args: argparse.Namespace) -> None:
    if getattr(args, "subject", None) is not None:
        payload["subject"] = args.subject
    if getattr(args, "description", None) is not None:
        payload["description"] = {"format": "markdown", "raw": args.description}
    if getattr(args, "start_date", None) is not None:
        payload["startDate"] = args.start_date
    if getattr(args, "due_date", None) is not None:
        payload["dueDate"] = args.due_date

    maybe_add_wp_links(payload, args)


def build_work_package_filters(args: argparse.Namespace) -> list[dict[str, Any]]:
    filters: list[dict[str, Any]] = []
    filter_specs = (
        ("project_id", "project"),
        ("assignee_id", "assignee"),
        ("responsible_id", "responsible"),
        ("status_id", "status"),
        ("type_id", "type"),
        ("priority_id", "priority"),
    )
    for attr_name, filter_name in filter_specs:
        value = getattr(args, attr_name, None)
        if value is not None:
            filters.append({filter_name: {"operator": "=", "values": [str(value)]}})
    return filters


def build_time_entry_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if args.body is not None:
        body_payload = parse_body(args.body)
        if not isinstance(body_payload, dict):
            raise SystemExit("--body JSON for time entry commands must be an object")
        payload.update(body_payload)
    return payload


def cmd_me(args: argparse.Namespace) -> int:
    return perform_request(args, "GET", "/users/me")


def cmd_projects(args: argparse.Namespace) -> int:
    if args.subcommand == "list":
        extra_filters: list[dict[str, Any]] = []
        if args.active_only:
            extra_filters.append({"active": {"operator": "=", "values": ["t"]}})
        return perform_request(
            args,
            "GET",
            "/projects",
            query=build_collection_query(args, extra_filters=extra_filters),
        )
    if args.subcommand == "get":
        return perform_request(args, "GET", f"/projects/{args.project_id}")
    if args.subcommand == "create":
        return perform_request(
            args,
            "POST",
            "/projects",
            body_obj=parse_body(args.body),
        )
    if args.subcommand == "update":
        return perform_request(
            args,
            "PATCH",
            f"/projects/{args.project_id}",
            body_obj=parse_body(args.body),
        )
    if args.subcommand == "delete":
        return perform_request(args, "DELETE", f"/projects/{args.project_id}")
    if args.subcommand == "status":
        return perform_request(args, "GET", f"/project_statuses/{args.status_id}")
    if args.subcommand == "configuration":
        return perform_request(args, "GET", f"/projects/{args.project_id}/configuration")
    if args.subcommand == "copy":
        return perform_request(
            args,
            "POST",
            f"/projects/{args.project_id}/copy",
            body_obj=parse_body(args.body) if args.body is not None else None,
        )
    if args.subcommand == "categories":
        return perform_request(
            args,
            "GET",
            f"/projects/{args.project_id}/categories",
            query=build_collection_query(args),
        )
    if args.subcommand == "memberships":
        return perform_request(
            args,
            "GET",
            f"/projects/{args.project_id}/memberships",
            query=build_collection_query(args),
        )
    if args.subcommand == "queries":
        return perform_request(
            args,
            "GET",
            f"/projects/{args.project_id}/queries",
            query=build_collection_query(args),
        )
    if args.subcommand == "types":
        return perform_request(
            args,
            "GET",
            f"/projects/{args.project_id}/types",
            query=build_collection_query(args),
        )
    if args.subcommand == "versions":
        return perform_request(
            args,
            "GET",
            f"/projects/{args.project_id}/versions",
            query=build_collection_query(args),
        )
    if args.subcommand == "work-packages":
        extra_filters = build_work_package_filters(args)
        extra_filters.insert(0, {"project": {"operator": "=", "values": [str(args.project_id)]}})
        return perform_request(
            args,
            "GET",
            "/work_packages",
            query=build_collection_query(args, extra_filters=extra_filters),
        )
    raise SystemExit(f"Unsupported projects subcommand: {args.subcommand}")


def cmd_work_packages(args: argparse.Namespace) -> int:
    if args.subcommand == "attachments":
        return perform_request(args, "GET", f"/work_packages/{args.work_package_id}/attachments")
    if args.subcommand == "attach-file":
        from .attachment_commands import upload_attachment

        return upload_attachment(
            args,
            Path(args.path).expanduser(),
            container_type="work-package",
            container_id=args.work_package_id,
        )
    if args.subcommand == "list":
        return perform_request(
            args,
            "GET",
            "/work_packages",
            query=build_collection_query(args, extra_filters=build_work_package_filters(args)),
        )
    if args.subcommand == "get":
        return perform_request(args, "GET", f"/work_packages/{args.work_package_id}")
    if args.subcommand == "create":
        create_payload: dict[str, Any] = {}
        maybe_add_wp_fields(create_payload, args)
        if args.body is not None:
            body_payload = parse_body(args.body)
            if not isinstance(body_payload, dict):
                raise SystemExit("--body JSON for create must be an object")
            create_payload.update(body_payload)
        if "subject" not in create_payload:
            raise SystemExit("Missing required field: --subject")
        return perform_request(
            args,
            "POST",
            f"/projects/{args.project_id}/work_packages",
            body_obj=create_payload,
        )
    if args.subcommand == "update":
        update_payload: dict[str, Any] = {}
        if args.body is not None:
            body_payload = parse_body(args.body)
            if not isinstance(body_payload, dict):
                raise SystemExit("--body JSON for update must be an object")
            update_payload.update(body_payload)
        maybe_add_wp_fields(update_payload, args)
        if args.lock_version is not None:
            update_payload["lockVersion"] = args.lock_version
        if "lockVersion" not in update_payload:
            base_url, auth_header, timeout = auth_context(args)
            current_url = build_url(base_url, f"/work_packages/{args.work_package_id}", [])
            cur_status, _, cur_body = request("GET", current_url, auth_header, None, timeout)
            cur_json = maybe_parse_json(cur_body)
            if not (
                200 <= cur_status < 300 and isinstance(cur_json, dict) and "lockVersion" in cur_json
            ):
                raise SystemExit(
                    "Unable to infer lockVersion automatically. Pass --lock-version explicitly."
                )
            update_payload["lockVersion"] = cur_json["lockVersion"]
        return perform_request(
            args,
            "PATCH",
            f"/work_packages/{args.work_package_id}",
            body_obj=update_payload,
        )
    if args.subcommand == "delete":
        expected = f"delete-{args.work_package_id}"
        if args.yes:
            if args.confirm_delete != expected:
                raise SystemExit(
                    f"Delete requires --confirm-delete {expected} when used with --yes."
                )
        else:
            print(f"Deletion confirmation required for work package {args.work_package_id}.")
            answer = input(f"Type '{expected}' to continue: ").strip()
            if answer != expected:
                raise SystemExit("Delete request cancelled.")
        return perform_request(args, "DELETE", f"/work_packages/{args.work_package_id}")
    if args.subcommand == "activities":
        return perform_request(
            args,
            "GET",
            f"/work_packages/{args.work_package_id}/activities",
            query=build_collection_query(args),
        )
    if args.subcommand == "comment":
        payload = parse_body(args.body)
        if not isinstance(payload, dict):
            raise SystemExit("--body JSON for comment must be an object")
        return perform_request(
            args,
            "POST",
            f"/work_packages/{args.work_package_id}/activities",
            body_obj=payload,
        )
    endpoint_suffixes = {
        "available-assignees": "available_assignees",
        "available-projects": "available_projects",
        "available-watchers": "available_watchers",
        "relation-candidates": "available_relations",
    }
    if args.subcommand in endpoint_suffixes:
        return perform_request(
            args,
            "GET",
            f"/work_packages/{args.work_package_id}/{endpoint_suffixes[args.subcommand]}",
            query=build_collection_query(args),
        )
    raise SystemExit(f"Unsupported work-packages subcommand: {args.subcommand}")


def cmd_request(args: argparse.Namespace) -> int:
    method = args.method.upper()
    body_obj = parse_body(args.body)
    return perform_request(args, method, args.path, query=args.query, body_obj=body_obj)


def cmd_login(args: argparse.Namespace) -> int:
    saved = load_saved_config()

    base_url = args.base_url or os.getenv("OP_BASE_URL") or saved.get("base_url")
    if not base_url:
        base_url = input("OpenProject base URL: ").strip()
        if not base_url:
            raise SystemExit("Base URL is required.")

    username = args.username or os.getenv("OP_USERNAME") or saved.get("username") or "apikey"
    auth_mode = args.auth_mode or os.getenv("OP_AUTH_MODE") or saved.get("auth_mode") or "auto"

    try:
        token = load_token(args.token, args.token_file, saved)
    except SystemExit:
        token = getpass.getpass("OpenProject API token: ").strip()
        if not token:
            raise SystemExit("Token is required.")

    auth_header = build_auth_header(auth_mode, token, username)
    effective_username = username

    if not args.no_test:
        test_url = build_url(base_url, "/users/me", [])
        status, _, body = request("GET", test_url, auth_header, None, args.timeout)
        if not (200 <= status < 300):
            if auth_mode in {"auto", "basic"} and username != "apikey":
                fallback_header = build_auth_header("basic", token, "apikey")
                fb_status, _, _ = request("GET", test_url, fallback_header, None, args.timeout)
                if 200 <= fb_status < 300:
                    effective_username = "apikey"
                else:
                    raise SystemExit(f"Login test failed with HTTP {status}: {body}")
            else:
                raise SystemExit(f"Login test failed with HTTP {status}: {body}")

    config = {
        "base_url": base_url,
        "username": effective_username,
        "auth_mode": auth_mode,
        "token": token,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    path = save_config(config)
    print(f"Saved OpenProject credentials to {path}")
    print(f"base_url={base_url}")
    print(f"username={effective_username}")
    print(f"auth_mode={auth_mode}")
    if effective_username != username:
        print("note=Switched username to 'apikey' for API token Basic auth compatibility")
    return 0
