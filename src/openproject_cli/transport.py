from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

READ_ONLY_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def build_url(base_url: str, path: str, query: list[str]) -> str:
    cleaned = path if path.startswith("/") else f"/{path}"
    if not cleaned.startswith("/api/"):
        cleaned = f"/api/v3{cleaned}"

    query_params: list[tuple[str, str]] = []
    for item in query:
        if "=" not in item:
            raise SystemExit(f"Invalid --query value '{item}'. Expected key=value.")
        key, value = item.split("=", 1)
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
            f"Refusing {method} request to {url}. "
            "Add --allow-write to permit state-changing methods."
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
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return exc.code, dict(exc.headers.items()) if exc.headers else {}, raw


def parse_body(body: str | None) -> Any:
    if body is None:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON passed to --body: {exc}") from exc
