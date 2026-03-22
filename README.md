# openproject-cli

[![Release](https://img.shields.io/github/v/release/decent-tools-for-thought/openproject-cli?sort=semver)](https://github.com/decent-tools-for-thought/openproject-cli/releases)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-0BSD-green)

Small command-line client for OpenProject API v3 with explicit write safety.

> [!IMPORTANT]
> This codebase is entirely AI-generated. It is useful to me, I hope it might be useful to others, and issues and contributions are welcome.

## Why This Exists

- Browse projects and work packages from the shell.
- Keep state-changing requests gated behind explicit confirmation.
- Make automation possible without losing safe defaults.

## Install

```bash
python -m pip install .
openproject --help
```

For local development:

```bash
uv sync
uv run openproject --help
```

## Quick Start

Log in once:

```bash
uv run openproject login \
  --base-url "https://openproject.example.org" \
  --username "apikey" \
  --token-file /path/to/token.txt
```

Read-only workflows:

```bash
uv run openproject me
uv run openproject projects list --page-size 10
uv run openproject work-packages list --project-id 1 --page-size 10
```

Write workflows require opt-in:

```bash
uv run openproject work-packages create 1 \
  --subject "Example task" \
  --allow-write
```

## Authentication

Resolution priority:

1. Command-line flags
2. Environment variables such as `OP_API_TOKEN` and `OP_BASE_URL`
3. Saved config from `openproject login`

Write methods (`POST`, `PUT`, `PATCH`, `DELETE`) never run unless `--allow-write` is provided.

## Development

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest
```

## Credits

This client builds on OpenProject API v3 and is not affiliated with OpenProject. Credit goes to the OpenProject project for the upstream platform and API documentation.
