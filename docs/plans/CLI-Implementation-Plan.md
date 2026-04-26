# GTD CLI — TDD Phased Implementation Plan

_March 2026_

## Overview

Build a command-line interface (`gtd`) for the GTD TODOs application. The CLI communicates with the running server over HTTP using API key authentication, stored locally in `~/.gtd/config.toml`. It provides full task and project management, daily GTD reports, and export functionality — all without opening a browser.

### Key Design Decisions

| Decision | Choice |
|---|---|
| **Language** | Python 3.12 (matches server stack) |
| **CLI framework** | `click` — idiomatic, composable, excellent `--help` formatting |
| **HTTP client** | `httpx` — already a dev dependency, async-capable, modern API |
| **Config format** | TOML at `~/.gtd/config.toml` — human-readable, Python stdlib `tomllib` for reads |
| **Config writes** | `tomli_w` — small dependency for writing TOML (stdlib `tomllib` is read-only) |
| **Output format** | Rich terminal tables via `rich` + plain-text fallback with `--plain` flag |
| **Package layout** | `cli/` directory at repo root with its own `pyproject.toml` |
| **Entry point** | Console script `gtd` registered via `[project.scripts]` |
| **Installation** | `pipx install .` or `uv tool install .` from `cli/` dir — no venv activation needed |
| **Install scripts** | `scripts/install-cli.sh` (macOS/Linux) that auto-detects `pipx` or `uv` |
| **Auth storage** | API key stored in `~/.gtd/config.toml` with `0600` permissions |
| **ASCII art** | Custom GTD banner displayed on `--help` via a `click.Group` subclass |
| **Skill file** | `.github/skills/gtd-cli/SKILL.md` for agent discoverability |
| **Testing** | `pytest` with `click.testing.CliRunner` + `httpx` mock/respx for HTTP |

### ASCII Art Banner

```
   ██████╗ ████████╗██████╗     ████████╗ ██████╗ ██████╗  ██████╗ ███████╗
  ██╔════╝ ╚══██╔══╝██╔══██╗    ╚══██╔══╝██╔═══██╗██╔══██╗██╔═══██╗██╔════╝
  ██║  ███╗   ██║   ██║  ██║       ██║   ██║   ██║██║  ██║██║   ██║███████╗
  ██║   ██║   ██║   ██║  ██║       ██║   ██║   ██║██║  ██║██║   ██║╚════██║
  ╚██████╔╝   ██║   ██████╔╝       ██║   ╚██████╔╝██████╔╝╚██████╔╝███████║
   ╚═════╝    ╚═╝   ╚═════╝        ╚═╝    ╚═════╝ ╚═════╝  ╚═════╝ ╚══════╝
                        Getting Things Done — CLI
```

Shown at the top of `gtd --help` output. Suppressed on subcommand help and non-TTY output.

---

## Directory Structure

```
cli/
├── pyproject.toml          # standalone package: gtd-cli
├── README.md               # CLI-specific usage docs
├── src/
│   └── gtd_cli/
│       ├── __init__.py
│       ├── main.py          # click group, ASCII banner, top-level options
│       ├── config.py        # config read/write (~/.gtd/config.toml)
│       ├── client.py        # HTTP client wrapper (httpx + auth header)
│       ├── commands/
│       │   ├── __init__.py
│       │   ├── config_cmd.py    # gtd config
│       │   ├── tasks.py         # gtd tasks, gtd add, gtd edit, gtd complete, gtd reopen
│       │   ├── projects.py      # gtd projects, gtd project
│       │   ├── views.py         # gtd today, gtd inbox
│       │   ├── export.py        # gtd export
│       │   ├── report.py        # gtd report
│       │   └── health.py        # gtd health
│       └── display.py       # rich table rendering + plain-text fallback
├── tests/
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_client.py
│   ├── test_commands_config.py
│   ├── test_commands_tasks.py
│   ├── test_commands_projects.py
│   ├── test_commands_views.py
│   ├── test_commands_export.py
│   ├── test_commands_report.py
│   └── test_commands_health.py
scripts/
└── install-cli.sh           # cross-platform install script
```

---

## Config File Format

`~/.gtd/config.toml`:

```toml
[server]
url = "http://localhost:8080"

[auth]
api_key = "gtd_abc123..."
```

- The `~/.gtd/` directory and `config.toml` are created by `gtd config init`.
- File permissions are set to `0600` (owner read/write only) to protect the API key.
- `GTD_API_KEY` and `GTD_SERVER_URL` environment variables override config values (useful for CI/agents).

---

## CLI Commands

### Global Options

```
gtd [--server URL] [--plain] [--help] [--version] COMMAND
```

| Flag | Purpose |
|---|---|
| `--server URL` | Override server URL for this invocation |
| `--plain` | Disable rich formatting (tables become tab-separated) |
| `--help` | Show ASCII banner + command list |
| `--version` | Print CLI version |

### Command Reference

| Command | Description | Server Endpoint |
|---|---|---|
| `gtd config init` | Interactive setup: prompt for server URL + API key, write config | — |
| `gtd config show` | Print current config (masked API key) | — |
| `gtd config set KEY VALUE` | Set a single config value | — |
| `gtd health` | Check server connectivity | `GET /health` |
| `gtd inbox` | List inbox tasks | `GET /export/tasks.json?status=inbox` |
| `gtd today` | Show overdue + due-today tasks | `GET /export/tasks.json` (client-side filter) |
| `gtd tasks` | List/filter tasks | `GET /export/tasks.json` + query params |
| `gtd tasks --status STATUS` | Filter by GTD status | `GET /export/tasks.json?status=STATUS` |
| `gtd tasks --search QUERY` | Search tasks by text | `GET /export/tasks.json` + client-side filter |
| `gtd tasks --project ID` | Filter by project | `GET /export/tasks.json` + client-side filter |
| `gtd add TITLE` | Create a new task | `POST /tasks` |
| `gtd add TITLE --project ID` | Create task in a project | `POST /tasks` |
| `gtd complete ID` | Complete a task | `POST /tasks/{id}/complete` |
| `gtd reopen ID` | Reopen a task | `POST /tasks/{id}/reopen` |
| `gtd edit ID --title T` | Update task fields | `POST /tasks/{id}/update` |
| `gtd edit ID --status S` | Change task status | `POST /tasks/{id}/quick-update` |
| `gtd edit ID --due DATE` | Set/change due date | `POST /tasks/{id}/quick-update` |
| `gtd edit ID --project ID` | Assign to project | `POST /tasks/{id}/quick-update` |
| `gtd projects` | List all projects | `GET /export/projects.json` |
| `gtd project ID` | Show project with its tasks | `GET /export/projects.json` + `GET /export/tasks.json` |
| `gtd export tasks [--format FMT]` | Export tasks (json/csv) | `GET /export/tasks.{fmt}` |
| `gtd export projects [--format FMT]` | Export projects (json/csv) | `GET /export/projects.{fmt}` |
| `gtd report [--date DATE]` | Structured GTD data summary (agent adds recommendations) | `GET /export/tasks.json` + `GET /export/projects.json` |

### Mutation Commands and Redirect Handling

The server's mutation routes (`POST /tasks`, `/tasks/{id}/complete`, etc.) are designed for browser form submissions — they accept `application/x-www-form-urlencoded` data and respond with HTTP 303/302 redirects. The CLI must:

1. Send form-encoded POST data (not JSON).
2. Disable automatic redirect following (`httpx` parameter: `follow_redirects=False`).
3. Treat a `3xx` response as success.
4. Print a confirmation message and optionally re-fetch the updated resource.

This approach avoids requiring any server-side changes.

---

## `cli/pyproject.toml`

```toml
[project]
name = "gtd-cli"
version = "0.1.0"
description = "Command-line interface for GTD TODOs"
requires-python = ">=3.12"
dependencies = [
    "click>=8.1,<9.0",
    "httpx>=0.28,<1.0",
    "rich>=13.0,<14.0",
    "tomli_w>=1.0,<2.0",
]

[project.scripts]
gtd = "gtd_cli.main:cli"

[dependency-groups]
dev = [
    "pytest>=8.3,<9.0",
    "respx>=0.22,<1.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/gtd_cli"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]
```

---

## Installation Scripts

### `scripts/install-cli.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

# GTD CLI Installer
# Installs the gtd command globally using pipx or uv tool install.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_DIR="$(cd "$SCRIPT_DIR/../cli" && pwd)"

echo "Installing GTD CLI from $CLI_DIR ..."

if command -v pipx &>/dev/null; then
    echo "Found pipx — installing with pipx..."
    pipx install "$CLI_DIR" --force
elif command -v uv &>/dev/null; then
    echo "Found uv — installing with uv tool..."
    uv tool install "$CLI_DIR" --force
else
    echo "Error: Neither pipx nor uv found."
    echo "Install one of:"
    echo "  brew install pipx   # or: python -m pip install --user pipx"
    echo "  brew install uv     # or: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo ""
echo "✓ GTD CLI installed! Run 'gtd --help' to get started."
echo "  First-time setup: gtd config init"
```

### Uninstall

```bash
pipx uninstall gtd-cli
# or
uv tool uninstall gtd-cli
```

---

## Phase Structure

### Phase 1 — Config Module & CLI Skeleton

**Goal:** Create the `cli/` package structure, config read/write module, ASCII art banner, and `gtd config` commands. No HTTP calls yet.

#### New Files

| File | Purpose |
|------|---------|
| `cli/pyproject.toml` | Package definition with dependencies and console script entry point |
| `cli/src/gtd_cli/__init__.py` | Package init with version |
| `cli/src/gtd_cli/main.py` | Click group with ASCII art banner, global options `--server`, `--plain`, `--version` |
| `cli/src/gtd_cli/config.py` | `load_config()`, `save_config()`, `get_config_path()`, `ensure_config_dir()` |
| `cli/src/gtd_cli/commands/__init__.py` | Commands package |
| `cli/src/gtd_cli/commands/config_cmd.py` | `gtd config init`, `gtd config show`, `gtd config set` |

#### Config Module Functions

```python
def get_config_dir() -> Path:
    """Return ~/.gtd, respecting GTD_CONFIG_DIR env override."""

def get_config_path() -> Path:
    """Return ~/.gtd/config.toml."""

def ensure_config_dir() -> Path:
    """Create ~/.gtd/ with 0700 permissions if it doesn't exist."""

def load_config() -> dict:
    """Read and return config dict. Returns defaults if file missing."""

def save_config(config: dict) -> None:
    """Write config dict to TOML file with 0600 permissions."""

def get_server_url(ctx_override: str | None = None) -> str:
    """Resolve server URL: CLI flag > env var > config file > default."""

def get_api_key() -> str | None:
    """Resolve API key: env var > config file."""
```

#### `gtd config init` Behavior

1. Prompt for server URL (default: `http://localhost:8080`).
2. Prompt for API key (hidden input).
3. Write `~/.gtd/config.toml` with `0600` permissions.
4. Print confirmation.

#### `gtd config show` Behavior

1. Print server URL.
2. Print masked API key (`gtd_••••••<last6>`), or "not set".

#### `gtd config set` Behavior

1. Accept `server.url` or `auth.api_key` as the key.
2. Update only the specified value in the config file.

#### ASCII Art Banner Implementation

Subclass `click.Group` to override `format_help()`:

```python
class GTDBanner(click.Group):
    BANNER = r"""
   ██████╗ ████████╗██████╗     ████████╗ ██████╗ ██████╗  ██████╗ ███████╗
  ██╔════╝ ╚══██╔══╝██╔══██╗    ╚══██╔══╝██╔═══██╗██╔══██╗██╔═══██╗██╔════╝
  ██║  ███╗   ██║   ██║  ██║       ██║   ██║   ██║██║  ██║██║   ██║███████╗
  ██║   ██║   ██║   ██║  ██║       ██║   ██║   ██║██║  ██║██║   ██║╚════██║
  ╚██████╔╝   ██║   ██████╔╝       ██║   ╚██████╔╝██████╔╝╚██████╔╝███████║
   ╚═════╝    ╚═╝   ╚═════╝        ╚═╝    ╚═════╝ ╚═════╝  ╚═════╝ ╚══════╝
                        Getting Things Done — CLI
    """

    def format_help(self, ctx, formatter):
        if ctx.info_name == "gtd":
            formatter.write(self.BANNER + "\n")
        super().format_help(ctx, formatter)
```

#### Tests (`cli/tests/test_config.py`, `cli/tests/test_commands_config.py`)

**Config module tests:**

1. `test_get_config_dir_default` — Returns `~/.gtd`.
2. `test_get_config_dir_env_override` — Respects `GTD_CONFIG_DIR`.
3. `test_ensure_config_dir_creates` — Creates directory with `0700`.
4. `test_save_config_permissions` — File is created with `0600`.
5. `test_load_config_missing_file` — Returns defaults when no file.
6. `test_load_save_roundtrip` — Save then load returns same data.
7. `test_get_server_url_priority` — CLI flag > env var > config > default.
8. `test_get_api_key_env_override` — `GTD_API_KEY` env var takes precedence.

**Config command tests:**

9. `test_config_init_creates_file` — `gtd config init` with input creates config.
10. `test_config_show_masked_key` — Shows masked API key.
11. `test_config_show_no_key` — Shows "not set" when no key.
12. `test_config_set_server_url` — `gtd config set server.url ...` updates config.
13. `test_config_set_api_key` — `gtd config set auth.api_key ...` updates config.

**Banner test:**

14. `test_help_shows_ascii_banner` — `gtd --help` output contains the banner.
15. `test_subcommand_help_no_banner` — `gtd config --help` does not contain the banner.
16. `test_version_flag` — `gtd --version` prints the version.

#### Acceptance Criteria

- [ ] `cli/` directory exists with valid `pyproject.toml`
- [ ] `uv sync` in `cli/` installs dependencies
- [ ] `uv run pytest` in `cli/` passes all tests
- [ ] `gtd --help` displays ASCII art banner
- [ ] `gtd config init` creates `~/.gtd/config.toml`
- [ ] Config file has `0600` permissions
- [ ] Environment variables override config values

---

### Phase 2 — HTTP Client & Health Command

**Goal:** Implement the HTTP client wrapper and the `gtd health` command to establish the server connectivity pattern.

#### New / Changed Files

| File | Purpose |
|------|---------|
| `cli/src/gtd_cli/client.py` | `GTDClient` class wrapping `httpx.Client` with auth header and base URL |
| `cli/src/gtd_cli/commands/health.py` | `gtd health` command |

#### HTTP Client Design

```python
class GTDClient:
    """HTTP client for the GTD TODOs API."""

    def __init__(self, base_url: str, api_key: str | None = None):
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self._client = httpx.Client(
            base_url=base_url,
            headers=headers,
            follow_redirects=False,
            timeout=10.0,
        )

    def get(self, path: str, **kwargs) -> httpx.Response: ...
    def post_form(self, path: str, data: dict, **kwargs) -> httpx.Response: ...
    def health(self) -> dict: ...
    def get_tasks(self, status: str | None = None) -> list[dict]: ...
    def get_projects(self) -> list[dict]: ...
    def create_task(self, title: str, project_id: int | None = None) -> None: ...
    def complete_task(self, task_id: int) -> None: ...
    def reopen_task(self, task_id: int) -> None: ...
    def update_task(self, task_id: int, **fields) -> None: ...
    def quick_update_task(self, task_id: int, field: str, value: str) -> None: ...
    def export_tasks(self, fmt: str = "json", status: str | None = None) -> str | list: ...
    def export_projects(self, fmt: str = "json") -> str | list: ...
```

Key behaviors:
- `follow_redirects=False` — mutation routes return `3xx`; treat as success.
- All methods raise `click.ClickException` on HTTP errors with human-readable messages.
- `post_form` sends `application/x-www-form-urlencoded` (matching the server's form-based routes).

#### `gtd health` Behavior

1. Call `GET /health`.
2. Print `✓ Server is healthy (URL)` on success.
3. Print `✗ Server unreachable: <error>` on failure (exit code 1).

#### Tests

**Client tests (`cli/tests/test_client.py`):**

1. `test_client_sets_auth_header` — Constructor sets `Authorization` header.
2. `test_client_no_auth_header_without_key` — No header when `api_key` is `None`.
3. `test_health_returns_status` — Mocked `GET /health` returns parsed JSON.
4. `test_get_tasks_returns_list` — Mocked `GET /export/tasks.json` returns parsed list.
5. `test_get_tasks_with_status_filter` — Sends `?status=inbox` query param.
6. `test_post_form_sends_encoded_data` — POST sends form-encoded body.
7. `test_post_form_treats_redirect_as_success` — A `303` response does not raise.
8. `test_http_error_raises_click_exception` — `4xx`/`5xx` raises `click.ClickException`.
9. `test_connection_error_raises_click_exception` — Network error raises `click.ClickException`.

**Health command tests (`cli/tests/test_commands_health.py`):**

10. `test_health_success` — Prints success message, exit code 0.
11. `test_health_failure` — Prints error message, exit code 1.

#### Acceptance Criteria

- [ ] HTTP client handles auth, form POSTs, and redirect responses
- [ ] Error handling produces human-readable click exceptions
- [ ] `gtd health` validates server connectivity
- [ ] All mocked tests pass without a running server

---

### Phase 3 — Task Commands

**Goal:** Implement task listing, filtering, creation, completion, reopening, and editing.

#### New / Changed Files

| File | Purpose |
|------|---------|
| `cli/src/gtd_cli/display.py` | Table rendering with `rich` and `--plain` fallback |
| `cli/src/gtd_cli/commands/tasks.py` | `gtd tasks`, `gtd add`, `gtd complete`, `gtd reopen`, `gtd edit` |

#### Display Module

```python
def render_task_table(tasks: list[dict], plain: bool = False) -> str:
    """Render a list of tasks as a formatted table.
    Columns: ID, Title, Status, Due Date, Project, Recurring.
    Color-code overdue (red) and due-today (blue) dates."""

def render_project_table(projects: list[dict], plain: bool = False) -> str:
    """Render a list of projects as a formatted table.
    Columns: ID, Name, Description, Due Date, Tasks."""

def render_task_detail(task: dict, plain: bool = False) -> str:
    """Render a single task's full details including notes."""
```

#### Command Behaviors

**`gtd tasks`**

```
gtd tasks [--status STATUS] [--search QUERY] [--project ID] [--due yes|no] [--recurring yes|no]
```

- Fetches all tasks from `GET /export/tasks.json` with optional `?status=` server-side filter.
- Applies additional client-side filters for `--search`, `--project`, `--due`, `--recurring`.
- Renders as a rich table (or tab-separated with `--plain`).

**`gtd add TITLE`**

```
gtd add "Buy groceries" [--project ID]
```

- POST to `/tasks` with form data `title=...` and optional `project_id=...`.
- Prints `✓ Task created: "Buy groceries"`.

**`gtd complete ID`**

- POST to `/tasks/{id}/complete`.
- Prints `✓ Task {id} completed`.

**`gtd reopen ID`**

- POST to `/tasks/{id}/reopen`.
- Prints `✓ Task {id} reopened`.

**`gtd edit ID [--title T] [--status S] [--due DATE] [--project ID] [--notes TEXT]`**

- If only one field is changed and it's `status`, `due_date`, or `project_id` → use `POST /tasks/{id}/quick-update`.
- Otherwise → use `POST /tasks/{id}/update` with all provided fields.
- Prints `✓ Task {id} updated`.

#### Tests (`cli/tests/test_commands_tasks.py`)

1. `test_tasks_list_renders_table` — `gtd tasks` with mocked data shows a table.
2. `test_tasks_filter_by_status` — `gtd tasks --status inbox` passes status to server.
3. `test_tasks_search_filters_client_side` — `--search` filters by title substring.
4. `test_tasks_plain_output` — `--plain` produces tab-separated output.
5. `test_add_task` — `gtd add "Test"` sends POST and prints confirmation.
6. `test_add_task_with_project` — `--project 1` includes `project_id` in form data.
7. `test_complete_task` — `gtd complete 1` sends POST to complete endpoint.
8. `test_reopen_task` — `gtd reopen 1` sends POST to reopen endpoint.
9. `test_edit_task_status_uses_quick_update` — `gtd edit 1 --status next_action` uses quick-update.
10. `test_edit_task_title_uses_full_update` — `gtd edit 1 --title "New"` uses full update.
11. `test_edit_task_due_date` — `gtd edit 1 --due 2026-04-01` sets due date.
12. `test_edit_task_clear_due_date` — `gtd edit 1 --due ""` clears due date.
13. `test_complete_nonexistent_shows_error` — 404 response shows error message.

#### Acceptance Criteria

- [ ] Tasks can be listed, filtered, and searched from the CLI
- [ ] Tasks can be created with an optional project assignment
- [ ] Tasks can be completed and reopened
- [ ] Task fields can be edited (single-field uses quick-update)
- [ ] Rich tables render with color-coded due dates
- [ ] `--plain` flag produces machine-parseable output

---

### Phase 4 — View & Project Commands

**Goal:** Implement `gtd today`, `gtd inbox`, `gtd projects`, and `gtd project`.

#### New / Changed Files

| File | Purpose |
|------|---------|
| `cli/src/gtd_cli/commands/views.py` | `gtd today`, `gtd inbox` |
| `cli/src/gtd_cli/commands/projects.py` | `gtd projects`, `gtd project ID` |

#### Command Behaviors

**`gtd today`**

- Fetches all tasks from `GET /export/tasks.json`.
- Client-side filtering: non-done tasks with `due_date` ≤ today.
- Groups into "Overdue" and "Due Today" sections.
- Shows count summary: `3 overdue, 5 due today`.

**`gtd inbox`**

- Fetches tasks with `GET /export/tasks.json?status=inbox`.
- Renders as a task table.
- Shows count: `12 tasks in inbox`.

**`gtd projects`**

- Fetches projects from `GET /export/projects.json`.
- Fetches tasks from `GET /export/tasks.json` to compute open task counts.
- Renders project table with task counts.

**`gtd project ID`**

- Fetches the project from `GET /export/projects.json` and finds by ID.
- Fetches tasks from `GET /export/tasks.json`, filters by `project_id`.
- Displays project metadata (name, description, notes, due date).
- Groups tasks by GTD status (matching the web UI layout).

#### Tests

**View commands (`cli/tests/test_commands_views.py`):**

1. `test_today_shows_overdue_and_due_today` — Correct grouping of tasks by date.
2. `test_today_excludes_done_tasks` — Done tasks are filtered out.
3. `test_today_excludes_no_due_date` — Tasks without due dates are excluded.
4. `test_today_shows_count_summary` — Output includes count summary.
5. `test_inbox_shows_inbox_tasks` — Only inbox status tasks shown.
6. `test_inbox_shows_count` — Output includes count.

**Project commands (`cli/tests/test_commands_projects.py`):**

7. `test_projects_list_with_counts` — Shows projects with task counts.
8. `test_project_detail_shows_metadata` — Shows name, description, notes.
9. `test_project_detail_groups_tasks` — Tasks grouped by status.
10. `test_project_not_found_shows_error` — Non-existent ID shows error.

#### Acceptance Criteria

- [ ] `gtd today` shows overdue and due-today tasks in separate sections
- [ ] `gtd inbox` shows only inbox tasks with count
- [ ] `gtd projects` shows projects with open-task counts
- [ ] `gtd project ID` shows project details with tasks grouped by status

---

### Phase 5 — Export & Report Commands

**Goal:** Implement `gtd export` and `gtd report` for data portability and daily GTD focus reports.

#### New / Changed Files

| File | Purpose |
|------|---------|
| `cli/src/gtd_cli/commands/export.py` | `gtd export tasks`, `gtd export projects` |
| `cli/src/gtd_cli/commands/report.py` | `gtd report` |

#### Command Behaviors

**`gtd export tasks [--format json|csv] [--status STATUS] [--output FILE]`**

- Fetches from `GET /export/tasks.{format}` with optional `?status=`.
- Writes to stdout or `--output FILE`.

**`gtd export projects [--format json|csv] [--output FILE]`**

- Fetches from `GET /export/projects.{format}`.
- Writes to stdout or `--output FILE`.

**`gtd report [--date DATE] [--tomorrow]`**

Generates a **structured data summary** of all tasks classified by GTD methodology — no LLM required. The CLI handles data fetching, date math, and deterministic classification. An agent (or human) reads the output and adds prioritization advice, context batching, and actionable recommendations.

**Design rationale:** The `gtd-daily-report` skill's real value is in the "GTD Recommendations" section — insightful, context-aware advice like two-minute rule suggestions or project health flags. That requires LLM reasoning. Baking an AI client into the CLI would add unnecessary complexity, an AI provider API key, and a dependency that doesn't belong. Instead, the CLI does the **data work** and the agent does the **thinking**.

**What the CLI does (deterministic):**

1. Fetch all tasks + projects via export endpoints.
2. Determine target date (`--date`, `--tomorrow`, or today).
3. Classify tasks into sections:
   - **Hard Landscape**: tasks due on target date (non-negotiable commitments).
   - **Overdue**: tasks due before target date (not done).
   - **Urgent Next Actions**: `next_action` status, due within 3 days.
   - **Other Next Actions**: remaining `next_action` tasks.
   - **Waiting For**: `waiting_for` tasks (with days waiting calculated).
   - **Inbox**: unclarified `inbox` tasks.
   - **Someday / Maybe**: `someday_maybe` tasks (brief mention).
4. Render as structured Markdown:
   - H2 title with target date.
   - "Do First" section (hard landscape + overdue items in a table).
   - Next actions table (title, project name, due date, days remaining).
   - Waiting-for table (title, project, days waiting).
   - Inbox count with list of titles.
   - Previous day's completed tasks count.
5. Output to stdout.

**What the agent adds (LLM-powered, via the `gtd-daily-report` skill):**

- 3-5 actionable GTD recommendations referencing specific tasks.
- Two-minute rule suggestions.
- Context batching advice.
- Follow-up nudges for long-waiting items.
- Project health flags (active projects with zero next actions).
- Friday weekly review reminder.

**Agent workflow:** The `gtd-daily-report` skill instructs the agent to run `gtd report`, read the structured output, then layer on its own analysis and recommendations.

#### Tests

**Export commands (`cli/tests/test_commands_export.py`):**

1. `test_export_tasks_json_stdout` — JSON output to stdout.
2. `test_export_tasks_csv_stdout` — CSV output to stdout.
3. `test_export_tasks_with_status_filter` — Passes status to server.
4. `test_export_tasks_to_file` — `--output` writes to file.
5. `test_export_projects_json` — Projects exported as JSON.

**Report command (`cli/tests/test_commands_report.py`):**

6. `test_report_generates_markdown` — Output is valid Markdown with H2 title.
7. `test_report_hard_landscape_section` — Due-today tasks appear in "Do First".
8. `test_report_overdue_tasks` — Overdue tasks appear in "Do First".
9. `test_report_next_actions_table` — Next action tasks appear in table with days remaining.
10. `test_report_waiting_for_with_days` — Waiting tasks show days-waiting count.
11. `test_report_inbox_count` — Inbox section shows count and task titles.
12. `test_report_tomorrow_flag` — `--tomorrow` shifts target date by 1 day.
13. `test_report_custom_date` — `--date 2026-04-01` uses specified date.
14. `test_report_project_name_resolution` — Project names shown instead of IDs.
15. `test_report_completed_count` — Shows previous day's completion count.

#### Acceptance Criteria

- [ ] `gtd export tasks` outputs JSON or CSV to stdout or file
- [ ] `gtd export projects` outputs JSON or CSV to stdout or file
- [ ] `gtd report` generates a structured data summary with classified tasks
- [ ] Report contains deterministic sections (Do First, Next Actions, Waiting For, Inbox)
- [ ] No LLM or AI dependencies — agent adds recommendations on top
- [ ] Project names are resolved from IDs in the report

---

### Phase 6 — Install Scripts, Skill File & Documentation

**Goal:** Create installation scripts, the CLI skill file, and update all documentation.

#### New / Changed Files

| File | Purpose |
|------|---------|
| `scripts/install-cli.sh` | macOS/Linux installer |
| `cli/README.md` | CLI usage documentation |
| `.github/skills/gtd-cli/SKILL.md` | Skill file for agent CLI usage |
| `.github/copilot-instructions.md` | Add CLI skill reference |
| `docs/llm-integration.md` | Add CLI as alternative to HTTP or direct SQLite |
| `README.md` | Add CLI section |

#### Skill File: `.github/skills/gtd-cli/SKILL.md`

```yaml
---
name: gtd-cli
description: Using the GTD CLI to manage tasks, projects, and generate reports from the command line.
---
```

The skill file should document:

1. **Prerequisites** — CLI installed (`gtd --version` to verify), config initialized (`~/.gtd/config.toml`).
2. **Quick start** — `gtd config init`, `gtd health`.
3. **Common workflows** — Add a task, complete a task, check today, generate a report.
4. **GTD report generation** — `gtd report` produces structured data; the agent reads it and adds LLM-powered recommendations. No API key in agent memory needed — the CLI reads from `~/.gtd/config.toml`.
5. **Environment variable overrides** — `GTD_API_KEY`, `GTD_SERVER_URL` for CI or agent contexts.
6. **Output formats** — Rich tables by default, `--plain` for machine parsing, JSON/CSV via export.
7. **Error handling** — How to diagnose connectivity issues.
8. **Full command reference** — Quick table of all commands.

#### `.github/copilot-instructions.md` Addition

Add to the Skills section:

```markdown
- **GTD CLI** (`.github/skills/gtd-cli/SKILL.md`): When using the command line to manage tasks, projects, or generate reports instead of the HTTP API directly.
```

#### `README.md` CLI Section

```markdown
## CLI

The GTD CLI provides command-line access to the running GTD TODOs server.

### Install

```bash
./scripts/install-cli.sh
```

### First-Time Setup

```bash
gtd config init
```

### Usage

```bash
gtd today            # show overdue + due-today tasks
gtd inbox            # show inbox
gtd add "Buy milk"   # quick-add a task
gtd complete 42      # complete a task
gtd report           # daily GTD focus report
gtd --help           # full command reference
```
```

#### Tests

1. `test_install_script_is_executable` — Shell script has execute permission.
2. `test_install_script_syntax` — `bash -n scripts/install-cli.sh` passes.

#### Acceptance Criteria

- [ ] `scripts/install-cli.sh` installs the CLI via `pipx` or `uv tool`
- [ ] `cli/README.md` documents all commands and installation
- [ ] `.github/skills/gtd-cli/SKILL.md` exists and is referenced in copilot-instructions
- [ ] Main `README.md` has a CLI section
- [ ] `docs/llm-integration.md` mentions CLI as an agent tool
- [ ] All existing server tests continue to pass

---

## Security Considerations

1. **API key stored with restricted permissions** — `~/.gtd/config.toml` is written with `0600` (owner-only). The directory is `0700`.
2. **Key never logged or echoed** — `gtd config show` masks the key. `gtd config init` uses hidden input.
3. **Environment variable override** — `GTD_API_KEY` lets CI/agents pass keys without writing to disk.
4. **No key in command history** — API key is prompted interactively, not passed as a CLI argument.
5. **HTTPS recommended for remote servers** — The CLI works over HTTP for local use, but docs recommend HTTPS for remote deployments.
6. **No credential caching beyond config** — The CLI reads the key per-invocation; no in-memory caching across commands.

---

## Future Enhancements (Out of Scope)

- Shell completions (`click` supports generating bash/zsh/fish completions).
- `gtd watch` — live-updating today view using polling.
- `gtd sync` — offline mode with local SQLite cache and sync on reconnect.
- Interactive TUI mode (e.g., with `textual`).
- Homebrew formula for `brew install gtd-cli`.
- Cross-compilation to standalone binary via `PyInstaller` or `nuitka`.
