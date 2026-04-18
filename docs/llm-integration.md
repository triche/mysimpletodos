# LLM Integration Guide

The repository includes `.github` customization assets so a new agent conversation can work from code and documentation instead of relying on prior chat state.

## Ground Rules

- Work phase-by-phase using test-driven development.
- Use the repository docs, tests, and `.github` assets as the source of truth.
- Keep API behavior, docs, and skill files synchronized.
- Preserve the architectural constraints: FastAPI, server-rendered pages, SQLite persistence, single-record recurring tasks, and Markdown notes rendered safely.

## Local App Assumptions

- Docker Compose starts the app on `http://localhost:8080`.
- The canonical persistent database path is `/data/todo.db` in the container.
- Health checks are available at `GET /health`.
- The home page (`GET /`) redirects to the inbox.

## Core Workflow Routes

- `GET /inbox` — inbox page with quick-add form.
- `GET /today` — tasks due today and overdue tasks.
- `GET /projects` — project list with task counts.
- `GET /projects/{id}` — project detail with tasks grouped by status.
- `GET /tasks` — all tasks page with filtering and search.
- `GET /tasks/{id}/edit` — edit form for a task.
- `POST /tasks` — create a task (form field: `title`, optional `project_id`).
- `POST /tasks/{id}/update` — update task from edit form.
- `POST /tasks/{id}/complete` — complete a task.
- `POST /tasks/{id}/reopen` — reopen a completed task.
- `POST /projects` — create a project (form field: `name`).

See `docs/api.md` for full route and form field documentation.

## All Tasks Filtering and Search

The `GET /tasks` page supports query parameters for filtering and text search:

| Parameter | Values | Meaning |
|---|---|---|
| `q` | free text | Search title and notes (case-insensitive) |
| `status` | `inbox`, `next_action`, `waiting_for`, `scheduled`, `someday_maybe`, `done` | Exact status match |
| `project_id` | integer or `none` | Filter by project; `none` for unassigned tasks |
| `has_due_date` | `yes`, `no` | Filter by due-date presence |
| `is_recurring` | `yes`, `no` | Filter by recurring flag |

Parameters can be combined. Example: `/tasks?status=inbox&q=groceries`

## Visual Distinction

The app uses CSS classes to visually distinguish task states:

- `.task-overdue` — red left border for overdue items
- `.task-due-today` — blue left border for items due today
- `.task-done` — faded with strike-through title
- `.task-inbox` — amber left border for inbox items

Status badges use per-status colors to help quickly identify task state.

## Export and Backup

The app provides export endpoints for portable data backups:

- `GET /export/tasks.csv` — CSV export of all tasks (optional `status` filter).
- `GET /export/tasks.json` — JSON export of all tasks (optional `status` filter).
- `GET /export/projects.csv` — CSV export of all projects.
- `GET /export/projects.json` — JSON export of all projects.

The SQLite database file can also be copied directly from the Docker volume:

```bash
docker compose cp todo-app:/data/todo.db ./backup.db
```

## Logging and Error Handling

The application logs all requests with method, path, status code, and latency to stdout in a structured format. Lifecycle events, exports, and errors are also logged.

HTTP errors (404, 500) return branded HTML error pages with navigation links.

## API Key Authentication

API keys enable programmatic access without a browser session. Generate keys from the Settings page (gear icon) after logging in with a passkey.

Use the key in the `Authorization` header:

```bash
curl -H "Authorization: Bearer mst_your_key_here" http://localhost:8080/export/tasks.json
```

This is the recommended way for LLM agents to authenticate when fetching task and project data.

## MST CLI

The `mst` command-line tool provides an alternative to direct HTTP calls or SQLite queries. Install it with `./scripts/install-cli.sh` and configure with `mst config init`.

This is the recommended way for agents to interact with the MySimpleTodos app:

```bash
# Check connectivity
mst health

# Generate a structured task report (agent adds recommendations)
mst report

# Export data
mst export tasks
mst export projects

# Manage tasks
mst add "Task title"
mst complete 42
```

The CLI reads the API key from `~/.mst/config.toml`, so agents don't need the key in memory.

See `.github/skills/mst-cli/SKILL.md` for the full agent skill reference.

## Companion Assets

- `.github/copilot-instructions.md`
- `.github/skills/todo-api/SKILL.md`
- `.github/skills/todo-data-model/SKILL.md`
- `.github/skills/mst-cli/SKILL.md`