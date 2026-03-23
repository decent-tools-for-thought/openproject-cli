<div align="center">

# openproject-cli

[![Release](https://img.shields.io/github/v/release/decent-tools-for-thought/openproject-cli?sort=semver&color=0f766e)](https://github.com/decent-tools-for-thought/openproject-cli/releases)
![Python](https://img.shields.io/badge/python-3.11%2B-0ea5e9)
![License](https://img.shields.io/badge/license-0BSD-14b8a6)

Safe-by-default command-line client for OpenProject API v3 with saved login support, read workflows, and explicitly gated writes.

</div>

> [!IMPORTANT]
> This codebase is entirely AI-generated. It is useful to me, I hope it might be useful to others, and issues and contributions are welcome.

## Map
- [Install](#install)
- [Functionality](#functionality)
- [Authentication](#authentication)
- [Quick Start](#quick-start)
- [Credits](#credits)

## Install
$$\color{#16A34A}Install \space \color{#22C55E}Tool$$

```bash
python -m pip install .    # install the package
openproject --help         # inspect available commands
```

## Functionality
$$\color{#16A34A}Login \space \color{#22C55E}Setup$$
- `openproject login`: save a base URL, token, username, and auth mode for later commands.
- `openproject login --no-test`: skip the `/users/me` credential test during setup.
- `openproject login`: supports token input from `--token`, `--token-file`, environment variables, or an interactive prompt.

$$\color{#16A34A}Read \space \color{#22C55E}Workflows$$
- `openproject me`: fetch the current authenticated user.
- `openproject projects list`: list projects with page size, offset, and raw OpenProject filter JSON.
- `openproject projects get <project-id>`: fetch one project.
- `openproject work-packages list`: list work packages globally or scoped to one project.
- `openproject work-packages get <work-package-id>`: fetch one work package.
- Read commands support `--output json|raw` and `--headers` for HTTP metadata.

$$\color{#16A34A}Write \space \color{#22C55E}Workflows$$
- `openproject work-packages create <project-id>`: create a work package with subject, description, type, status, priority, assignee, responsible user, start date, due date, and an additional merged JSON body.
- `openproject work-packages update <work-package-id>`: update a work package with explicit field flags or a merged JSON body.
- `openproject work-packages update`: auto-fetch `lockVersion` when omitted and use that for optimistic locking.
- `openproject work-packages delete <work-package-id>`: delete a work package with explicit confirmation text.

$$\color{#16A34A}Request \space \color{#22C55E}Safety$$
- `openproject request <path>`: send a generic API request to any OpenProject API path.
- `openproject request`: supports arbitrary HTTP methods, repeatable query parameters, and JSON request bodies.
- All state-changing requests require `--allow-write`.
- All state-changing requests can additionally require interactive confirmation unless `--yes` is passed.
- Deletion with `--yes` still requires an explicit `--confirm-delete delete-<id>` value.

## Authentication
$$\color{#16A34A}Access \space \color{#22C55E}Setup$$

Resolution priority:

1. Command-line flags
2. Environment variables such as `OP_API_TOKEN`, `OP_BASE_URL`, `OP_USERNAME`, and `OP_AUTH_MODE`
3. Saved config from `openproject login`

Write methods (`POST`, `PUT`, `PATCH`, `DELETE`) never run unless `--allow-write` is provided.

## Quick Start
$$\color{#16A34A}Try \space \color{#22C55E}Workflow$$

```bash
uv run openproject login \    # save base URL and token for later commands
  --base-url "https://openproject.example.org" \
  --username "apikey" \
  --token-file /path/to/token.txt

uv run openproject me                                      # fetch the current user
uv run openproject projects list --page-size 10           # list projects
uv run openproject work-packages list --project-id 1 --page-size 10    # list one project's work packages

uv run openproject work-packages create 1 \    # create a work package with write opt-in
  --subject "Example task" \
  --allow-write
```

## Credits

This client is built for OpenProject API v3 and is not affiliated with OpenProject.

Credit goes to the OpenProject project for the upstream platform, API model, and documentation this tool builds on.
