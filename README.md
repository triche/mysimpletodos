# GTD TODOs

GTD TODOs is a local-first task application for a single laptop user. FastAPI serves server-rendered HTML pages with small HTMX interactions, SQLite persists data, and the app is designed around GTD task states, optional due dates, recurring tasks, Markdown notes, and project organization with notes, due dates, and completion tracking.

![GTD TODOs logo](docs/gtd-todos-logo.png)

## Features

- **GTD workflow**: Inbox, Next Action, Waiting For, Scheduled, Someday/Maybe, and Done statuses.
- **Projects**: Group tasks under projects with their own notes, due dates, and completion state.
- **Recurring tasks**: Daily, weekly, monthly, or custom-interval recurrence. Completing a recurring task advances its due date instead of marking it done.
- **Markdown notes**: Task and project notes are stored as raw Markdown and rendered as safe HTML.
- **Quick updates**: Inline status, due date, and project changes from list views without opening the edit form.
- **Search**: Full-text search across tasks with filters for status, project, due date, and recurrence.
- **Export**: CSV and JSON export for tasks and projects.
- **Passkey auth**: Single-user WebAuthn authentication with API key support for programmatic access.
- **CSRF protection**: Double-submit cookie middleware on all mutation routes.

## Local Python Setup

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) (e.g. `brew install uv`).
2. Install the project with development dependencies.

```bash
uv sync
```

3. Run the app locally.

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

The default database URL is `sqlite:////data/todo.db`. For local development outside Docker, set `DATABASE_URL` to a writable path such as `sqlite:///./data/todo.db`.

## Docker Compose

The compose stack requires `AUTH_SECRET_KEY`. Generate one and export it (or add it to a `.env` file next to `docker-compose.yml`):

```bash
# Generate a secret
python -c "import secrets; print(secrets.token_hex(32))"

# Export it (or add AUTH_SECRET_KEY=<value> to .env)
export AUTH_SECRET_KEY=<value>
```

Start the app with a persistent named volume mounted at `/data`:

```bash
docker compose up --build
```

Stop the stack:

```bash
docker compose down
```

The container listens internally on port 8080 but is mapped to **port 8081** on the host: `http://localhost:8081`. The compose file sets `WEBAUTHN_ORIGIN` to `http://localhost:8081` by default to match.

## Authentication

GTD TODOs supports single-user passkey (WebAuthn) authentication. On first visit a passkey is registered, and subsequent access requires authenticating with that passkey.

### Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `APP_NAME` | Application display name | `GTD TODOs` |
| `APP_ENV` | Environment (`development` / `production`) | `development` |
| `APP_HOST` | Bind address | `0.0.0.0` |
| `APP_PORT` | Listen port | `8080` |
| `DATABASE_URL` | SQLite connection string | `sqlite:////data/todo.db` |
| `TZ` | Container timezone | *(unset; compose sets `America/Chicago`)* |
| `AUTH_DISABLED` | Disable auth entirely (for local dev / existing tests) | `false` |
| `AUTH_SECRET_KEY` | Secret for signing session cookies | *auto-generated* |
| `AUTH_SESSION_MAX_AGE` | Session cookie max age in seconds | `604800` (7 days) |
| `WEBAUTHN_RP_ID` | WebAuthn Relying Party ID (domain) | `localhost` |
| `WEBAUTHN_RP_NAME` | Human-readable RP name | `GTD TODOs` |
| `WEBAUTHN_ORIGIN` | Expected origin for WebAuthn ceremonies | `http://localhost:8080` |

### API Keys (Programmatic Access)

API keys allow CLI tools and scripts to access the API without a browser session. Generate keys from the Settings page (gear icon in the nav bar) after logging in with a passkey.

Use the key in the `Authorization` header:

```bash
curl -H "Authorization: Bearer gtd_your_key_here" http://localhost:8080/export/tasks.json
```

Keys are shown in full once at creation time and stored as SHA-256 hashes. Up to 10 keys can be active. Revoke keys from the Settings page.

### Disabling Auth for Local Development

Set `AUTH_DISABLED=true` to skip all authentication:

```bash
AUTH_DISABLED=true uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### First-Run Setup

When no credentials exist in the database, visiting any page redirects to `/auth/setup` where you register a passkey. After setup, future visits go through the login flow at `/auth/login`.

## Routes

### Pages

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Redirects to `/inbox` |
| `GET` | `/inbox` | Inbox — tasks with `inbox` status and a quick-add form |
| `GET` | `/today` | Today — overdue tasks and tasks due today |
| `GET` | `/tasks` | All tasks — filterable by `status`, `project_id`, `has_due_date`, `is_recurring`, and free-text `q` search |
| `GET` | `/tasks/{id}/edit` | Edit form for a single task |
| `GET` | `/projects` | Projects list with optional `show` and `has_due_date` filters |
| `GET` | `/projects/{id}` | Project detail — tasks grouped by GTD status |
| `GET` | `/projects/{id}/edit` | Edit form for a single project |
| `GET` | `/settings` | Settings page — API key management |

### Task Mutations

| Method | Path | Description |
|---|---|---|
| `POST` | `/tasks` | Create a task (defaults to `inbox`). Accepts optional `project_id` |
| `POST` | `/tasks/{id}/update` | Update task fields from the edit form |
| `POST` | `/tasks/{id}/quick-update` | Inline single-field update (status, due date, or project) |
| `POST` | `/tasks/{id}/complete` | Complete a task. Recurring tasks advance `due_date`; others move to `done` |
| `POST` | `/tasks/{id}/reopen` | Reopen a completed task back to `inbox` |

### Project Mutations

| Method | Path | Description |
|---|---|---|
| `POST` | `/projects` | Create a new project |
| `POST` | `/projects/{id}/update` | Update project name, description, notes, and due date |
| `POST` | `/projects/{id}/complete` | Mark a project as completed |

### Export

| Method | Path | Description |
|---|---|---|
| `GET` | `/export/tasks.csv` | Export tasks as CSV (optional `status` filter) |
| `GET` | `/export/tasks.json` | Export tasks as JSON (optional `status` filter) |
| `GET` | `/export/projects.csv` | Export projects as CSV |
| `GET` | `/export/projects.json` | Export projects as JSON |

### Health

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Returns `{"status": "ok"}` |

See [docs/api.md](docs/api.md) for full API documentation including form fields and data model details.

## Backup and Restore

The SQLite database file is stored in the Docker volume at `/data/todo.db`. Back it up by copying the file or using the export endpoints:

```bash
# Copy the database file directly
docker compose cp todo-app:/data/todo.db ./backup-todo.db

# Or export data as CSV / JSON (use port 8081 for Docker Compose)
curl -o tasks.csv http://localhost:8081/export/tasks.csv
curl -o projects.json http://localhost:8081/export/projects.json
```

To restore, copy the backup into the running container and restart:

```bash
docker compose down
docker compose cp ./backup-todo.db todo-app:/data/todo.db
docker compose up
```

If the container is not available for `docker compose cp`, you can copy
directly into the named volume's mount point on the host:

```bash
# Find the volume's mount point
docker volume inspect gtd-todos_todo_app_data --format '{{ .Mountpoint }}'

# Copy the backup there (may require sudo on Linux)
sudo cp ./backup-todo.db "$(docker volume inspect gtd-todos_todo_app_data --format '{{ .Mountpoint }}')/todo.db"
```

See [docs/api.md](docs/api.md) for full export endpoint documentation.

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

### Commands

| Command | Description |
|---|---|
| `gtd today` | Show overdue + due-today tasks |
| `gtd inbox` | Show inbox tasks |
| `gtd tasks` | List/filter all tasks |
| `gtd add "Buy milk"` | Quick-add a task |
| `gtd complete 42` | Complete a task |
| `gtd reopen 42` | Reopen a completed task |
| `gtd edit 42 --status next_action` | Edit task fields |
| `gtd projects` | List projects |
| `gtd project 1` | Show project detail |
| `gtd export tasks` | Export tasks (JSON/CSV) |
| `gtd export projects` | Export projects (JSON/CSV) |
| `gtd report` | Daily GTD focus report |
| `gtd health` | Check server connectivity |
| `gtd config init` | Interactive config setup |
| `gtd config show` | Print current config |
| `gtd config set KEY VALUE` | Set a config value |

Global flags: `--server URL`, `--plain`, `--version`.

See [cli/README.md](cli/README.md) for full CLI documentation.

## Developer Commands

Run tests:

```bash
uv run pytest
```

Run lint checks:

```bash
uv run ruff check .
```

Run type checks:

```bash
uv run mypy app
```

Build the container image:

```bash
docker build .
```

## Project Structure

- `app/` — FastAPI application.
  - `routes/` — Page, task, project, auth, settings, export, and health route handlers.
  - `services/` — Service layer: task, project, auth, API key, export, and health operations.
  - `models.py` — SQLModel domain models (Task, Project, WebAuthnCredential, APIKey).
  - `templates/` — Jinja2 templates for server-rendered pages.
  - `static/` — CSS and JavaScript assets.
  - `csrf.py` — Double-submit cookie CSRF middleware.
  - `markdown.py` — Markdown-to-safe-HTML rendering.
  - `auth.py` — Session cookie creation and validation.
  - `config.py` — Environment-based settings.
  - `db.py` — SQLite engine and session management.
  - `seed.py` — Sample data seeding for local development.
  - `logging_config.py` — Structured logging setup.
- `cli/` — GTD CLI package: command-line interface for the server.
- `scripts/` — Utility scripts (e.g. `install-cli.sh`, `backup-db.sh`).
- `tests/` — Pytest suite covering routes, services, auth, security, search, and more.
- `docs/` — Human-readable API, LLM integration, and planning documentation.
- `.github/` — Copilot instructions, skills, and CI workflow.

## Documentation

- [docs/api.md](docs/api.md)
- [docs/llm-integration.md](docs/llm-integration.md)
- [.github/skills/todo-api/SKILL.md](.github/skills/todo-api/SKILL.md)
- [.github/skills/todo-data-model/SKILL.md](.github/skills/todo-data-model/SKILL.md)
- [.github/skills/gtd-cli/SKILL.md](.github/skills/gtd-cli/SKILL.md)
- [cli/README.md](cli/README.md)