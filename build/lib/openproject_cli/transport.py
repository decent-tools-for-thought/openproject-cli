from __future__ import annotations

import json
import secrets
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
    content_type = None
    if body_obj is not None:
        data = json.dumps(body_obj).encode("utf-8")
        content_type = "application/json"
    return request_bytes(method, url, auth_header, data, timeout, content_type=content_type)


def request_bytes(
    method: str,
    url: str,
    auth_header: str,
    body: bytes | None,
    timeout: int,
    *,
    content_type: str | None = None,
) -> tuple[int, dict[str, str], str]:
    headers = {
        "Authorization": auth_header,
        "Accept": "application/hal+json, application/json",
        "User-Agent": "openproject-cli/0.1",
    }
    if content_type is not None:
        headers["Content-Type"] = content_type

    req = urllib.request.Request(url=url, method=method, data=body, headers=headers)
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


def build_multipart_form_data(
    *,
    metadata: dict[str, Any],
    filename: str,
    file_content: bytes,
    file_content_type: str,
) -> tuple[str, bytes]:
    boundary = f"openproject-cli-{secrets.token_hex(12)}"
    escaped_filename = filename.replace("\\", "\\\\").replace('"', '\\"')
    metadata_json = json.dumps(metadata, ensure_ascii=True).encode("utf-8")
    boundary_bytes = boundary.encode("ascii")

    parts = [
        b"--" + boundary_bytes + b"\r\n"
        b'Content-Disposition: form-data; name="metadata"\r\n'
        b"Content-Type: application/json\r\n\r\n" + metadata_json + b"\r\n",
        b"--"
        + boundary_bytes
        + b"\r\n"
        + f'Content-Disposition: form-data; name="file"; filename="{escaped_filename}"\r\n'.encode(
            "utf-8"
        )
        + f"Content-Type: {file_content_type}\r\n\r\n".encode("ascii")
        + file_content
        + b"\r\n",
        b"--" + boundary_bytes + b"--\r\n",
    ]
    return f"multipart/form-data; boundary={boundary}", b"".join(parts)
