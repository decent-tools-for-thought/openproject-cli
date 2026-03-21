# OpenProject CLI

Small command-line client for OpenProject API v3.

## Features

- Safe-by-default: only read-only methods (`GET`, `HEAD`, `OPTIONS`) run without confirmation.
- State-changing methods (`POST`, `PUT`, `PATCH`, `DELETE`) require `--allow-write` and an interactive `yes` confirmation (or `--yes`).
- Auth token loading priority:
  - `--token`
  - `OP_API_TOKEN` environment variable
  - `--token-file`
  - saved login config (`openproject login`)
- Auth mode:
  - `auto` (default): uses Bearer if token starts with `opapi-`, otherwise Basic with username `apikey`.
  - `bearer`
  - `basic`

## Quick start

Set up the repo with `uv`:

```bash
uv sync
uv run openproject --help
```

Save credentials once, then run commands without passing token/url each time:

```bash
uv run openproject login --base-url "https://openproject.example.org" --username "apikey" --token-file /path/to/token.txt
uv run openproject me
```

List projects:

```bash
uv run openproject projects list --page-size 10
```

Get one project:

```bash
uv run openproject projects get 1
```

List work packages (all):

```bash
uv run openproject work-packages list --page-size 10
```

List work packages for one project:

```bash
uv run openproject work-packages list --project-id 1 --page-size 10
```

Create a work package (requires explicit write permission):

```bash
uv run openproject work-packages create 1 --subject "Example task" --description "Created via CLI" --allow-write
```

Update a work package (lock version is auto-fetched if omitted):

```bash
uv run openproject work-packages update 123 --subject "Renamed task" --allow-write
```

Delete a work package (extra safeguard):

```bash
uv run openproject work-packages delete 123 --allow-write
```

Non-interactive delete requires an explicit confirmation token:

```bash
uv run openproject work-packages delete 123 --allow-write --yes --confirm-delete delete-123
```

Generic request (read-only):

```bash
uv run openproject request /projects --query pageSize=5
```

Generic write request (explicitly allowed + confirmed):

```bash
uv run openproject request /work_packages --method POST --allow-write --body '{"subject":"Example"}'
```

To skip prompt for automation:

```bash
uv run openproject request /work_packages --method POST --allow-write --yes --body '{"subject":"Example"}'
```

## Configuration

- `OP_BASE_URL`
- `OP_API_TOKEN`
- `OP_USERNAME` (used only for Basic auth, default `apikey`)
- `OPENPROJECT_CLI_CONFIG` (optional custom path for saved login config)

Credential resolution priority:

1. Command-line flags (`--token`, `--base-url`, `--username`, `--auth-mode`)
2. Environment variables (`OP_API_TOKEN`, `OP_BASE_URL`, `OP_USERNAME`, `OP_AUTH_MODE`)
3. Saved login config (`openproject login`)

For a no-install module invocation, use `python -m openproject_cli ...`.

There is no built-in default URL.

Default saved config path:

- `~/.config/openproject-cli/config.json`

## Notes

- OpenProject API docs: <https://www.openproject.org/docs/api/introduction/>
- If your token is not an `opapi-...` token, Basic auth is typically required.
- Write commands never run unless `--allow-write` is provided.
- Delete commands require additional confirmation (`delete-<id>`).

## Releases

Tagging `v<version>` builds and verifies the packaged distributions, then publishes them:

- `openproject_cli-<version>.tar.gz`
- `openproject_cli-<version>-py3-none-any.whl`
- `SHA256SUMS`
