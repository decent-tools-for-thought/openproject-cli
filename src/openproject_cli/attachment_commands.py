from __future__ import annotations

import argparse
import mimetypes
from pathlib import Path
from typing import Any

from .commands import auth_context, render_response
from .transport import (
    build_multipart_form_data,
    build_url,
    confirm_write,
    maybe_parse_json,
    request_bytes,
)

ATTACHMENT_CONTAINER_PATHS = {
    "activity": "/activities/{container_id}/attachments",
    "meeting": "/meetings/{container_id}/attachments",
    "post": "/posts/{container_id}/attachments",
    "wiki-page": "/wiki_pages/{container_id}/attachments",
    "work-package": "/work_packages/{container_id}/attachments",
}


def attachment_container_path(container_type: str, container_id: int) -> str:
    return ATTACHMENT_CONTAINER_PATHS[container_type].format(container_id=container_id)


def upload_attachment(
    args: argparse.Namespace,
    path: Path,
    *,
    container_type: str | None = None,
    container_id: int | None = None,
) -> int:
    if not path.exists():
        raise SystemExit(f"Attachment file does not exist: {path}")
    if not path.is_file():
        raise SystemExit(f"Attachment path is not a file: {path}")

    base_url, auth_header, timeout = auth_context(args)
    api_path = (
        "/attachments"
        if container_type is None or container_id is None
        else attachment_container_path(container_type, container_id)
    )
    url = build_url(base_url, api_path, [])
    confirm_write("POST", url, args.yes, args.allow_write)

    metadata: dict[str, Any] = {"fileName": args.file_name or path.name}
    if args.description:
        metadata["description"] = args.description

    file_content = path.read_bytes()
    file_type = (
        args.content_type
        or mimetypes.guess_type(path.name)[0]
        or "application/octet-stream"
    )
    content_type, body = build_multipart_form_data(
        metadata=metadata,
        filename=path.name,
        file_content=file_content,
        file_content_type=file_type,
    )

    status, headers, response_body = request_bytes(
        "POST",
        url,
        auth_header,
        body,
        timeout,
        content_type=content_type,
    )
    if not args.verify:
        return render_response(args, status, headers, response_body)
    if container_type is None or container_id is None:
        raise SystemExit("--verify is only supported for attachments uploaded to a container.")

    verify_url = build_url(base_url, attachment_container_path(container_type, container_id), [])
    verify_status, _, verify_body = request_bytes("GET", verify_url, auth_header, None, timeout)
    uploaded = maybe_parse_json(response_body)
    verified = maybe_parse_json(verify_body)
    payload = {"uploaded": uploaded, "verified": verified, "verifyStatus": verify_status}
    return render_response(args, status, headers, str_payload(payload))


def str_payload(payload: Any) -> str:
    import json

    return json.dumps(payload, ensure_ascii=True)


def cmd_attachments(args: argparse.Namespace) -> int:
    if args.subcommand == "get":
        return _request_attachment(args, "GET", f"/attachments/{args.attachment_id}")
    if args.subcommand == "delete":
        return _request_attachment(args, "DELETE", f"/attachments/{args.attachment_id}")
    if args.subcommand == "list":
        return _request_attachment(
            args,
            "GET",
            attachment_container_path(args.container_type, args.container_id),
        )
    if args.subcommand == "upload":
        return upload_attachment(
            args,
            Path(args.path).expanduser(),
            container_type=args.container_type,
            container_id=args.container_id,
        )
    if args.subcommand == "create":
        return upload_attachment(args, Path(args.path).expanduser())
    raise SystemExit(f"Unsupported attachments subcommand: {args.subcommand}")


def _request_attachment(args: argparse.Namespace, method: str, path: str) -> int:
    from .commands import perform_request

    return perform_request(args, method, path)
