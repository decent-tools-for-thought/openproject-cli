from __future__ import annotations

import json

from .transport import maybe_parse_json


def print_output(
    status: int,
    headers: dict[str, str],
    body: str,
    output: str,
    with_headers: bool,
) -> None:
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
