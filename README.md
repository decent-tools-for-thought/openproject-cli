# OpenProject CLI

Small command-line client for OpenProject API v3.

## Features

- Safe-by-default: only read-only methods (`GET`, `HEAD`, `OPTIONS`) run without confirmation.
- State-changing methods (`POST`, `PUT`, `PATCH`, `DELETE`) require `--allow-write` and an interactive `yes` confirmation (or `--yes`).
- Auth token loading priority:
  - `--token`
  - `OP_API_TOKEN` environment variable
  - `--token-file`
  - saved login config (`openproject_cli.py login`)
- Auth mode:
  - `auto` (default): uses Bearer if token starts with `opapi-`, otherwise Basic with username `apikey`.
  - `bearer`
  - `basic`

## Quick start

Save credentials once, then run commands without passing token/url each time:

```bash
./openproject_cli.py login --base-url "https://openproject.example.org" --username "apikey" --token-file /path/to/token.txt
./openproject_cli.py me
```

List projects:

```bash
./openproject_cli.py projects list --page-size 10
```

Get one project:

```bash
./openproject_cli.py projects get 1
```

List work packages (all):

```bash
./openproject_cli.py work-packages list --page-size 10
```

List work packages for one project:

```bash
./openproject_cli.py work-packages list --project-id 1 --page-size 10
```

Create a work package (requires explicit write permission):

```bash
./openproject_cli.py work-packages create 1 --subject "Example task" --description "Created via CLI" --allow-write
```

Update a work package (lock version is auto-fetched if omitted):

```bash
./openproject_cli.py work-packages update 123 --subject "Renamed task" --allow-write
```

Delete a work package (extra safeguard):

```bash
./openproject_cli.py work-packages delete 123 --allow-write
```

Non-interactive delete requires an explicit confirmation token:

```bash
./openproject_cli.py work-packages delete 123 --allow-write --yes --confirm-delete delete-123
```

Generic request (read-only):

```bash
./openproject_cli.py request /projects --query pageSize=5
```

Generic write request (explicitly allowed + confirmed):

```bash
./openproject_cli.py request /work_packages --method POST --allow-write --body '{"subject":"Example"}'
```

To skip prompt for automation:

```bash
./openproject_cli.py request /work_packages --method POST --allow-write --yes --body '{"subject":"Example"}'
```

## Configuration

- `OP_BASE_URL`
- `OP_API_TOKEN`
- `OP_USERNAME` (used only for Basic auth, default `apikey`)
- `OPENPROJECT_CLI_CONFIG` (optional custom path for saved login config)

Credential resolution priority:

1. Command-line flags (`--token`, `--base-url`, `--username`, `--auth-mode`)
2. Environment variables (`OP_API_TOKEN`, `OP_BASE_URL`, `OP_USERNAME`, `OP_AUTH_MODE`)
3. Saved login config (`openproject_cli.py login`)

There is no built-in default URL.

Default saved config path:

- `~/.config/openproject-cli/config.json`

## Notes

- OpenProject API docs: <https://www.openproject.org/docs/api/introduction/>
- If your token is not an `opapi-...` token, Basic auth is typically required.
- Write commands never run unless `--allow-write` is provided.
- Delete commands require additional confirmation (`delete-<id>`).

## Arch package

Arch packaging metadata is in `packaging/arch/` and is designed to install from a GitHub release tarball asset named:

- `openproject-cli-<version>.tar.gz`

Current packaging files:

- `packaging/arch/PKGBUILD`
- `packaging/arch/.SRCINFO`

### Release flow for Arch tarball source

1. Ensure `main` is up to date and your working tree is clean.
2. Run:

```bash
./scripts/release.sh 0.1.0
```

What this does:

- Creates and pushes git tag `v0.1.0`
- Creates GitHub release `v0.1.0`
- Downloads GitHub generated source tarball
- Renames and uploads it as release asset `openproject-cli-0.1.0.tar.gz`
- Computes SHA256 of that asset
- Updates `packaging/arch/PKGBUILD` (`pkgver`, `sha256sums`)
- Regenerates `packaging/arch/.SRCINFO`
- Creates a local commit for Arch metadata update

### Build check

```bash
cd packaging/arch
makepkg --printsrcinfo > .SRCINFO
makepkg -f
```
