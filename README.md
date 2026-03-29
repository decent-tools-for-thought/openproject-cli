<div align="center">

# openproject-cli

[![Release](https://img.shields.io/github/v/release/decent-tools-for-thought/openproject-cli?sort=semver&color=16a34a)](https://github.com/decent-tools-for-thought/openproject-cli/releases)
![Python](https://img.shields.io/badge/python-3.13%2B-15803d)
![License](https://img.shields.io/badge/license-0BSD-22c55e)

Safe-by-default command-line client for OpenProject API v3 with saved login support, comprehensive resource commands, and explicitly gated writes.

</div>

> [!IMPORTANT]
> This codebase is entirely AI-generated. It is useful to me, I hope it might be useful to others, and issues and contributions are welcome.

## Map
- [Install](#install)
- [Functionality](#functionality)
- [Configuration](#configuration)
- [Quick Start](#quick-start)
- [Credits](#credits)

## Install
$$\color{#15803D}Install \space \color{#22C55E}Tool$$

```bash
python -m pip install .    # install the package
openproject --help         # inspect available commands
```

## Functionality
$$\color{#15803D}Login \space \color{#22C55E}Setup$$
- `openproject login`: save a base URL, token, username, and auth mode for later commands.
- `openproject login --no-test`: skip the `/users/me` credential test during setup.
- `openproject login`: supports token input from `--token`, `--token-file`, environment variables, or an interactive prompt.

$$\color{#15803D}Resource \space \color{#22C55E}Surface$$
- `openproject root show`: inspect `/api/v3`.
- `openproject configuration show`: fetch global configuration.
- `openproject user-preferences show`: fetch current user preferences.
- `openproject attachments get|list|upload|create|delete`: work with attachment resources and multipart upload directly.
- `openproject attachments list|upload <container-type> <container-id>`: supports `activity`, `meeting`, `post`, `wiki-page`, and `work-package`.
- `openproject users list|get|current|create|update|delete`: manage users.
- `openproject projects list|get|create|update|delete|status|configuration|copy`: manage projects and project metadata.
- `openproject memberships list|get|create|update|delete`: manage memberships.
- `openproject queries list|get|create|update|delete`: manage saved work package queries.
- `openproject relations list|get|create|update|delete`: manage work package relations.
- `openproject time-entries list|get|create|update|delete`: manage time tracking entries.
- `openproject activities`, `categories`, `priorities`, `roles`, `statuses`, `time-entry-activities`, `types`, and `versions`: list and fetch these API resources directly.

$$\color{#15803D}Project \space \color{#22C55E}Workflows$$
- `openproject me`: fetch the current authenticated user.
- `openproject projects categories|memberships|queries|types|versions <project-id>`: inspect project-scoped collections.
- `openproject projects work-packages <project-id>`: list one project’s work packages with structured filter flags.
- `openproject work-packages list|get|create|update|delete`: manage work packages.
- `openproject work-packages attachments <id>`: list attachments on one work package.
- `openproject work-packages attach-file <id> <path>`: upload a file directly to one work package.
- `openproject work-packages activities <id>`: list work package activities.
- `openproject work-packages comment <id> --body ...`: create a work package activity comment.
- `openproject work-packages available-assignees|available-projects|available-watchers|relation-candidates <id>`: inspect common work package action endpoints.
- Collection commands support `--page-size`, `--offset`, raw `--filters`, and raw `--sort-by`.
- Read commands support `--output json|raw` and `--headers` for HTTP metadata.

$$\color{#15803D}Write \space \color{#22C55E}Workflows$$
- `openproject work-packages create <project-id>`: supports subject, description, type, status, priority, assignee, responsible user, start date, due date, and additional JSON.
- `openproject work-packages update <work-package-id>`: supports explicit field flags or a merged JSON body.
- `openproject work-packages update`: auto-fetches `lockVersion` when omitted and uses that for optimistic locking.
- `openproject work-packages delete <work-package-id>`: still requires explicit confirmation text.
- `openproject attachments upload work-package <id> <file> --description "..." --verify`: direct multipart upload to a work package and optional read-back verification.
- `openproject work-packages attach-file <id> <file> --description "..." --verify`: short alias for the same work-package upload path.
- `openproject attachments create <file>`: upload a containerless attachment only when you explicitly need that workflow.
- Generic create, update, and delete flows on resource commands accept `--body` with documented JSON payloads.

$$\color{#15803D}Request \space \color{#22C55E}Safety$$
- `openproject request <path>`: send a generic API request to any OpenProject API path.
- `openproject request`: supports arbitrary HTTP methods, repeatable query parameters, and JSON request bodies.
- All state-changing requests require `--allow-write`.
- All state-changing requests can additionally require interactive confirmation unless `--yes` is passed.
- Deletion with `--yes` still requires an explicit `--confirm-delete delete-<id>` value.
- `request` remains the escape hatch. The main workflows should now go through named commands.

$$\color{#15803D}Reference \space \color{#22C55E}Docs$$
- Command coverage was expanded against the official OpenProject API v3 endpoint docs:
  - https://www.openproject.org/docs/api/endpoints/
  - https://www.openproject.org/docs/api/endpoints/projects/
  - https://www.openproject.org/docs/api/endpoints/users/
  - https://www.openproject.org/docs/api/endpoints/attachments/
  - https://www.openproject.org/docs/api/endpoints/queries/
  - https://www.openproject.org/docs/api/endpoints/work-packages/
  - https://www.openproject.org/docs/api/endpoints/time-entries/

## Configuration
$$\color{#15803D}Access \space \color{#22C55E}Setup$$

Resolution priority:

1. Command-line flags
2. Environment variables such as `OP_API_TOKEN`, `OP_BASE_URL`, `OP_USERNAME`, and `OP_AUTH_MODE`
3. Saved config from `openproject login`

Write methods (`POST`, `PUT`, `PATCH`, `DELETE`) never run unless `--allow-write` is provided.

## Quick Start
$$\color{#15803D}Try \space \color{#22C55E}Workflow$$

```bash
uv run openproject login \    # save base URL and token for later commands
  --base-url "https://openproject.example.org" \
  --username "apikey" \
  --token-file /path/to/token.txt

uv run openproject root show                                              # inspect API root links
uv run openproject users current                                          # fetch the current user
uv run openproject projects list --active-only --page-size 10             # list active projects
uv run openproject projects work-packages 1 --status-id 6 --page-size 10  # list filtered work packages in one project
uv run openproject queries list --page-size 10                            # list saved queries

# preferred PDF upload path: direct to the work package container
uv run openproject attachments upload work-package 803 source.pdf \
  --description "Source PDF" \
  --verify \
  --allow-write

# equivalent work-package-specific shortcut
uv run openproject work-packages attach-file 803 source.pdf \
  --description "Source PDF" \
  --verify \
  --allow-write

uv run openproject work-packages create 1 \    # create a work package with write opt-in
  --subject "Example task" \
  --allow-write
```

## Credits

This client is built for OpenProject API v3 and is not affiliated with OpenProject.

Credit goes to the OpenProject project for the upstream platform, API model, and documentation this tool builds on.
