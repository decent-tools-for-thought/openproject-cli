from __future__ import annotations

import argparse
import getpass
import json
import os
from datetime import datetime, timezone
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


def cmd_me(args: argparse.Namespace) -> int:
    base_url, auth_mode, username, token = resolve_auth_settings(args)
    auth_header = build_auth_header(auth_mode, token, username)
    url = build_url(base_url, "/users/me", [])
    status, headers, body = request("GET", url, auth_header, None, args.timeout)
    print_output(status, headers, body, args.output, args.headers)
    return 0 if 200 <= status < 300 else 1


def cmd_projects(args: argparse.Namespace) -> int:
    base_url, auth_mode, username, token = resolve_auth_settings(args)
    auth_header = build_auth_header(auth_mode, token, username)

    if args.subcommand == "list":
        query = [f"pageSize={args.page_size}", f"offset={args.offset}"]
        if args.filters:
            query.append(f"filters={args.filters}")
        url = build_url(base_url, "/projects", query)
    else:
        url = build_url(base_url, f"/projects/{args.project_id}", [])

    status, headers, body = request("GET", url, auth_header, None, args.timeout)
    print_output(status, headers, body, args.output, args.headers)
    return 0 if 200 <= status < 300 else 1


def cmd_work_packages(args: argparse.Namespace) -> int:
    base_url, auth_mode, username, token = resolve_auth_settings(args)
    auth_header = build_auth_header(auth_mode, token, username)

    if args.subcommand == "list":
        query = [f"pageSize={args.page_size}", f"offset={args.offset}"]
        if args.project_id is not None:
            query.append(
                "filters="
                + json.dumps([{"project": {"operator": "=", "values": [str(args.project_id)]}}])
            )
        if args.filters:
            query.append(f"filters={args.filters}")
        url = build_url(base_url, "/work_packages", query)
    elif args.subcommand == "get":
        url = build_url(base_url, f"/work_packages/{args.work_package_id}", [])
        status, headers, body = request("GET", url, auth_header, None, args.timeout)
        print_output(status, headers, body, args.output, args.headers)
        return 0 if 200 <= status < 300 else 1
    elif args.subcommand == "create":
        url = build_url(base_url, f"/projects/{args.project_id}/work_packages", [])
        confirm_write("POST", url, args.yes, args.allow_write)

        create_payload: dict[str, Any] = {}
        maybe_add_wp_fields(create_payload, args)
        if "subject" not in create_payload:
            raise SystemExit("Missing required field: --subject")

        if args.body is not None:
            body_payload = parse_body(args.body)
            if not isinstance(body_payload, dict):
                raise SystemExit("--body JSON for create must be an object")
            create_payload.update(body_payload)

        status, headers, body = request("POST", url, auth_header, create_payload, args.timeout)
        print_output(status, headers, body, args.output, args.headers)
        return 0 if 200 <= status < 300 else 1
    elif args.subcommand == "update":
        url = build_url(base_url, f"/work_packages/{args.work_package_id}", [])
        confirm_write("PATCH", url, args.yes, args.allow_write)

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
            current_url = build_url(base_url, f"/work_packages/{args.work_package_id}", [])
            cur_status, _, cur_body = request("GET", current_url, auth_header, None, args.timeout)
            cur_json = maybe_parse_json(cur_body)
            if not (
                200 <= cur_status < 300 and isinstance(cur_json, dict) and "lockVersion" in cur_json
            ):
                raise SystemExit(
                    "Unable to infer lockVersion automatically. Pass --lock-version explicitly."
                )
            update_payload["lockVersion"] = cur_json["lockVersion"]

        status, headers, body = request("PATCH", url, auth_header, update_payload, args.timeout)
        print_output(status, headers, body, args.output, args.headers)
        return 0 if 200 <= status < 300 else 1
    elif args.subcommand == "delete":
        url = build_url(base_url, f"/work_packages/{args.work_package_id}", [])
        confirm_write("DELETE", url, args.yes, args.allow_write)

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

        status, headers, body = request("DELETE", url, auth_header, None, args.timeout)
        print_output(status, headers, body, args.output, args.headers)
        return 0 if 200 <= status < 300 else 1

    else:
        raise SystemExit(f"Unsupported work-packages subcommand: {args.subcommand}")

    status, headers, body = request("GET", url, auth_header, None, args.timeout)
    print_output(status, headers, body, args.output, args.headers)
    return 0 if 200 <= status < 300 else 1


def cmd_request(args: argparse.Namespace) -> int:
    base_url, auth_mode, username, token = resolve_auth_settings(args)
    auth_header = build_auth_header(auth_mode, token, username)
    method = args.method.upper()
    url = build_url(base_url, args.path, args.query)

    confirm_write(method, url, args.yes, args.allow_write)
    body_obj = parse_body(args.body)

    status, headers, body = request(method, url, auth_header, body_obj, args.timeout)
    print_output(status, headers, body, args.output, args.headers)
    return 0 if 200 <= status < 300 else 1


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
            # For token-based Basic auth, OpenProject expects username 'apikey'.
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
