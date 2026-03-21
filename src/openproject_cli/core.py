#!/usr/bin/env python3

"""Minimal OpenProject API v3 command-line client.

Defaults to safe, read-only behavior. Any state-changing HTTP method requires
explicit opt-in and confirmation.
"""

from __future__ import annotations

import argparse
import base64
import getpass
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


READ_ONLY_METHODS = {"GET", "HEAD", "OPTIONS"}


def default_config_path() -> Path:
    config_home = os.getenv("XDG_CONFIG_HOME")
    base_dir = Path(config_home).expanduser() if config_home else Path.home() / ".config"
    return base_dir / "openproject-cli" / "config.json"


def config_path() -> Path:
    raw = os.getenv("OPENPROJECT_CLI_CONFIG")
    return Path(raw).expanduser() if raw else default_config_path()


def load_saved_config() -> dict[str, Any]:
    path = config_path()
    if not path.exists():
        return {}

    try:
        content = path.read_text(encoding="utf-8")
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_config(config: dict[str, Any]) -> Path:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Keep file access private as it stores API credentials.
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass

    path.write_text(json.dumps(config, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass

    return path


def load_token(token_arg: str | None, token_file_arg: str | None, saved_config: dict[str, Any] | None = None) -> str:
    if token_arg:
        return token_arg.strip()

    env_token = os.getenv("OP_API_TOKEN")
    if env_token:
        return env_token.strip()

    candidate_files: list[Path] = []
    if token_file_arg:
        candidate_files.append(Path(token_file_arg))

    if not token_file_arg:
        config_token = (saved_config or {}).get("token")
        if isinstance(config_token, str) and config_token.strip():
            return config_token.strip()

    for file_path in candidate_files:
        if not file_path.exists():
            continue
        content = file_path.read_text(encoding="utf-8").strip()
        if not content:
            continue

        # Support either raw token or KEY=VALUE format.
        if "=" in content and not content.startswith("opapi-"):
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if key.strip() in {"OP_API_TOKEN", "OPENPROJECT_API_TOKEN", "API_TOKEN", "TOKEN"}:
                    return value.strip().strip('"').strip("'")

        return content

    raise SystemExit(
        "No API token found. Set OP_API_TOKEN, pass --token, provide --token-file, or run login."
    )


def require_base_url(args: argparse.Namespace, saved: dict[str, Any]) -> str:
    base_url = args.base_url or os.getenv("OP_BASE_URL") or saved.get("base_url")
    if not base_url:
        raise SystemExit(
            "No base URL configured. Pass --base-url, set OP_BASE_URL, or run `openproject-cli login --base-url <url>`."
        )
    return base_url


def resolve_auth_settings(args: argparse.Namespace) -> tuple[str, str, str, str]:
    saved = load_saved_config()
    base_url = require_base_url(args, saved)
    auth_mode = args.auth_mode or os.getenv("OP_AUTH_MODE") or saved.get("auth_mode") or "auto"
    username = args.username or os.getenv("OP_USERNAME") or saved.get("username") or "apikey"
    token = load_token(args.token, args.token_file, saved)
    return base_url, auth_mode, username, token


def build_auth_header(auth_mode: str, token: str, username: str | None) -> str:
    if auth_mode == "auto":
        # OpenProject API tokens usually have an opapi- prefix and work as Bearer.
        # Other token formats commonly work via Basic auth with user 'apikey'.
        auth_mode = "bearer" if token.startswith("opapi-") else "basic"

    if auth_mode == "bearer":
        return f"Bearer {token}"

    user = username or os.getenv("OP_USERNAME") or "apikey"
    basic = base64.b64encode(f"{user}:{token}".encode("utf-8")).decode("ascii")
    return f"Basic {basic}"


def build_url(base_url: str, path: str, query: list[str]) -> str:
    cleaned = path if path.startswith("/") else f"/{path}"
    if not cleaned.startswith("/api/"):
        cleaned = f"/api/v3{cleaned}"

    query_params: list[tuple[str, str]] = []
    for q in query:
        if "=" not in q:
            raise SystemExit(f"Invalid --query value '{q}'. Expected key=value.")
        key, value = q.split("=", 1)
        query_params.append((key, value))

    query_string = urllib.parse.urlencode(query_params, doseq=True)
    return urllib.parse.urljoin(base_url.rstrip("/") + "/", cleaned.lstrip("/")) + (
        f"?{query_string}" if query_string else ""
    )


def confirm_write(method: str, url: str, assume_yes: bool, allow_write: bool) -> None:
    if method in READ_ONLY_METHODS:
        return

    if not allow_write:
        raise SystemExit(
            f"Refusing {method} request to {url}. Add --allow-write to permit state-changing methods."
        )

    if assume_yes:
        return

    print(f"About to execute a state-changing request: {method} {url}")
    answer = input("Type 'yes' to continue: ").strip().lower()
    if answer != "yes":
        raise SystemExit("Write request cancelled.")


def maybe_parse_json(body: str) -> Any:
    stripped = body.strip()
    if not stripped:
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return body


def request(
    method: str,
    url: str,
    auth_header: str,
    body_obj: Any,
    timeout: int,
) -> tuple[int, dict[str, str], str]:
    data = None
    headers = {
        "Authorization": auth_header,
        "Accept": "application/hal+json, application/json",
        "User-Agent": "openproject-cli/0.1",
    }

    if body_obj is not None:
        data = json.dumps(body_obj).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url=url, method=method, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return resp.status, dict(resp.headers.items()), raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        return e.code, dict(e.headers.items()) if e.headers else {}, raw


def print_output(status: int, headers: dict[str, str], body: str, output: str, with_headers: bool) -> None:
    if with_headers:
        print(f"HTTP {status}")
        for key, value in headers.items():
            print(f"{key}: {value}")
        print()

    if output == "raw":
        print(body)
        return

    parsed = maybe_parse_json(body)
    if parsed is None:
        return
    if isinstance(parsed, str):
        print(parsed)
        return
    print(json.dumps(parsed, indent=2, ensure_ascii=True, sort_keys=False))


def parse_body(body: str | None) -> Any:
    if body is None:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON passed to --body: {exc}") from exc


def add_write_safety_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--allow-write", action="store_true", help="Allow state-changing API requests")
    parser.add_argument("--yes", action="store_true", help="Skip interactive write confirmation prompt")


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


def add_common_auth_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--token")
    parser.add_argument("--token-file", default=None)
    parser.add_argument("--auth-mode", choices=["auto", "bearer", "basic"], default=None)
    parser.add_argument(
        "--username",
        default=None,
        help="Used only when --auth-mode basic (for API token basic auth, OpenProject recommends username 'apikey').",
    )
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--output", choices=["json", "raw"], default="json")
    parser.add_argument("--headers", action="store_true", help="Include HTTP status and response headers")


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
            query.append(f"filters={json.dumps([{'project': {'operator': '=', 'values': [str(args.project_id)]}}])}")
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

        payload: dict[str, Any] = {}
        maybe_add_wp_fields(payload, args)
        if "subject" not in payload:
            raise SystemExit("Missing required field: --subject")

        if args.body is not None:
            body_payload = parse_body(args.body)
            if not isinstance(body_payload, dict):
                raise SystemExit("--body JSON for create must be an object")
            payload.update(body_payload)

        status, headers, body = request("POST", url, auth_header, payload, args.timeout)
        print_output(status, headers, body, args.output, args.headers)
        return 0 if 200 <= status < 300 else 1

    elif args.subcommand == "update":
        url = build_url(base_url, f"/work_packages/{args.work_package_id}", [])
        confirm_write("PATCH", url, args.yes, args.allow_write)

        payload: dict[str, Any] = {}
        if args.body is not None:
            body_payload = parse_body(args.body)
            if not isinstance(body_payload, dict):
                raise SystemExit("--body JSON for update must be an object")
            payload.update(body_payload)

        maybe_add_wp_fields(payload, args)

        if args.lock_version is not None:
            payload["lockVersion"] = args.lock_version

        if "lockVersion" not in payload:
            current_url = build_url(base_url, f"/work_packages/{args.work_package_id}", [])
            cur_status, _, cur_body = request("GET", current_url, auth_header, None, args.timeout)
            cur_json = maybe_parse_json(cur_body)
            if not (200 <= cur_status < 300 and isinstance(cur_json, dict) and "lockVersion" in cur_json):
                raise SystemExit(
                    "Unable to infer lockVersion automatically. Pass --lock-version explicitly."
                )
            payload["lockVersion"] = cur_json["lockVersion"]

        status, headers, body = request("PATCH", url, auth_header, payload, args.timeout)
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
                fb_status, _, fb_body = request("GET", test_url, fallback_header, None, args.timeout)
                if 200 <= fb_status < 300:
                    auth_header = fallback_header
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
    login.add_argument("--no-test", action="store_true", help="Skip credentials test against /users/me")
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
            "e.g. '[{\"active\":{\"operator\":\"=\",\"values\":[\"t\"]}}]'."
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
    req.add_argument("--query", action="append", default=[], help="Query parameter key=value (repeatable)")
    req.add_argument("--body", help="JSON payload for write requests")
    req.add_argument("--allow-write", action="store_true", help="Allow POST/PUT/PATCH/DELETE methods")
    req.add_argument("--yes", action="store_true", help="Skip interactive write confirmation prompt")
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
            action
            for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        ).choices[args.command].print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
