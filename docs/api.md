# API Overview

## Page Routes

- `GET /`: Redirects to `/inbox`.
- `GET /inbox`: Inbox page showing tasks with `inbox` status and a quick-add form.
- `GET /today`: Today page showing overdue tasks and tasks due today.
- `GET /projects`: Projects list showing all non-archived projects with task counts.
- `GET /projects/{project_id}`: Project detail page with tasks grouped by task status.
- `GET /tasks`: All tasks page with filtering and search.
- `GET /tasks/{task_id}/edit`: Edit form for a single task.

## Mutation Routes

- `POST /tasks`: Create a new task (defaults to `inbox` status). Accepts optional `project_id` for project quick-add. Redirects back to the referring page.
- `POST /tasks/{task_id}/update`: Update task fields from the edit form. Redirects to `/inbox`.
- `POST /tasks/{task_id}/complete`: Complete a task. Non-recurring tasks move to `done`; recurring tasks advance `due_date`. Redirects back to the referring page.
- `POST /tasks/{task_id}/reopen`: Reopen a completed task back to `inbox`. Redirects back to the referring page.
- `POST /projects`: Create a new project. Redirects to `/projects`.

## Operational Routes

- `GET /health`: Returns JSON health status.

## Authentication Methods

### Session Cookie (Browser)

Authenticate via the passkey login flow. A signed `mst_session` cookie is set after successful authentication.

### API Key (Programmatic Access)

Include the key in the `Authorization` header:

    Authorization: Bearer mst_your_key_here

API keys grant access to all protected routes (same scope as session cookies). API keys cannot be used to access the Settings page or manage other keys — those routes require a session cookie.

### Managing API Keys

- `GET /settings` — Settings page with API key management (requires session)
- `POST /settings/api-keys` — Generate a new key (requires session, form field: `name`)
- `POST /settings/api-keys/{key_id}/revoke` — Revoke a key (requires session)

Keys are shown in full exactly once at creation time. After that, only a masked suffix is displayed. Up to 10 keys can exist simultaneously.

## Authentication Routes

All routes except `/health`, `/auth/*`, and `/static/*` require an authenticated session (cookie or API key) when `AUTH_DISABLED` is not `true`.

- `GET /auth/setup`: First-run setup page (only when no credentials exist). Redirects to `/auth/login` if credentials already exist.
- `POST /auth/setup/options`: Returns `PublicKeyCredentialCreationOptions` JSON for WebAuthn registration.
- `POST /auth/setup/verify`: Verifies registration response, stores credential, sets session cookie. Accepts JSON body.
- `GET /auth/login`: Login page (redirects to `/auth/setup` if no credentials exist).
- `POST /auth/login/options`: Returns `PublicKeyCredentialRequestOptions` JSON for WebAuthn authentication.
- `POST /auth/login/verify`: Verifies authentication response, updates sign count, sets session cookie. Accepts JSON body.
- `POST /auth/logout`: Clears session cookie, redirects to `/auth/login`.

### Session Cookie

- Name: `mst_session`
- `HttpOnly`, `SameSite=Lax`, `Secure` (when origin is HTTPS)
- Signed with `itsdangerous.TimestampSigner` using `AUTH_SECRET_KEY`
- Max age configurable via `AUTH_SESSION_MAX_AGE` (default 7 days)

## Export Routes

- `GET /export/tasks.csv`: Export all tasks as CSV. Optional `status` query parameter to filter.
- `GET /export/tasks.json`: Export all tasks as JSON. Optional `status` query parameter to filter.
- `GET /export/projects.csv`: Export all projects as CSV.
- `GET /export/projects.json`: Export all projects as JSON.

All export responses include a `Content-Disposition` header with a date-stamped filename.

### `GET /health`

Response:

```json
{
  "status": "ok"
}
```

### `POST /tasks`

Form fields:

| Field | Required | Notes |
|---|---|---|
| `title` | Yes | Task title (empty titles are rejected) |

Redirects to `/inbox` on success.

### `POST /tasks/{task_id}/update`

Form fields:

| Field | Required | Notes |
|---|---|---|
| `title` | Yes | Task title |
| `notes` | No | Raw Markdown text |
| `status` | No | One of: `inbox`, `next_action`, `waiting_for`, `scheduled`, `someday_maybe`, `done` |
| `due_date` | No | ISO format date (`YYYY-MM-DD`) or empty to clear |
| `is_recurring` | No | Checkbox value (`on` when checked) |
| `recurrence_type` | No | One of: `daily`, `weekly`, `monthly`, `interval_days` |
| `recurrence_interval_days` | No | Integer, used with `interval_days` recurrence |
| `project_id` | No | Integer project ID or empty for no project |

Redirects to `/inbox` on success. Returns 404 if task not found.

### `POST /tasks/{task_id}/complete`

No form fields required. Redirects to `/inbox`. Returns 404 if task not found.

### `POST /tasks/{task_id}/reopen`

No form fields required. Redirects to `/inbox`. Returns 404 if task not found.

### `POST /projects`

Form fields:

| Field | Required | Notes |
|---|---|---|
| `name` | Yes | Project name (empty names are ignored) |

Redirects to `/projects` on success.

## Data Model

### Projects

| Column | Type | Notes |
|---|---|---|
| `id` | integer | Primary key, auto-generated |
| `name` | text | Required, unique |
| `description` | text | Optional |
| `created_at` | datetime | UTC timestamp |
| `updated_at` | datetime | UTC timestamp |
| `archived_at` | datetime | Optional, set when archived |

### Tasks

| Column | Type | Notes |
|---|---|---|
| `id` | integer | Primary key, auto-generated |
| `title` | text | Required |
| `notes` | text | Optional, raw Markdown |
| `status` | text | One of: `inbox`, `next_action`, `waiting_for`, `scheduled`, `someday_maybe`, `done` |
| `due_date` | date | Optional |
| `is_recurring` | boolean | Default `false` |
| `recurrence_type` | text | Optional: `daily`, `weekly`, `monthly`, `interval_days` |
| `recurrence_interval_days` | integer | Optional, used when `recurrence_type = interval_days` |
| `last_completed_at` | datetime | Set each time a recurring task is completed |
| `project_id` | integer | Optional foreign key to `projects.id` |
| `created_at` | datetime | UTC timestamp |
| `updated_at` | datetime | UTC timestamp |
| `completed_at` | datetime | Set when a non-recurring task is completed |

## Service Layer

### Project Operations

```python
create_project(session, name=..., description=...)  -> Project
get_project(session, project_id)                     -> Project | None
list_projects(session, include_archived=False)       -> list[Project]
update_project(session, project_id, name=..., description=...) -> Project | None
archive_project(session, project_id)                 -> Project | None
```

### Task Operations

```python
create_task(session, title=..., notes=..., status=..., due_date=...,
            is_recurring=..., recurrence_type=...,
            recurrence_interval_days=..., project_id=...) -> Task
get_task(session, task_id)                            -> Task | None
list_tasks(session, status=..., project_id=...)       -> list[Task]
search_tasks(session, status=..., project_id=...,
             no_project=..., q=..., has_due_date=...,
             is_recurring=...)                         -> list[Task]
update_task(session, task_id, **fields)               -> Task | None
complete_task(session, task_id)                        -> Task | None
reopen_task(session, task_id)                         -> Task | None
```

### Completion Behavior

- **Non-recurring tasks**: status moves to `done`, `completed_at` is set.
- **Recurring tasks**: `due_date` advances to the next occurrence, `last_completed_at` is set, status remains actionable (not `done`), `completed_at` stays `None`.

### Recurrence Advancement

| Type | Rule |
|---|---|
| `daily` | +1 day |
| `weekly` | +7 days |
| `monthly` | Same day next month (clamped to month end) |
| `interval_days` | +N days (from `recurrence_interval_days`) |

## Seed Data

Populate the database with sample data for local testing:

```bash
python -m app.seed
```

Future phases will expand this document with filtering, search, and HTMX partial behaviors.

---

## Today View

### `GET /today`

Displays two sections:

1. **Overdue** — Tasks whose `due_date` is before today and `status` is not `done`. Sorted by `due_date` ascending, then `created_at`.
2. **Due Today** — Tasks whose `due_date` equals today and `status` is not `done`. Sorted by `created_at`.

Recurring tasks whose next due date is today appear alongside one-time tasks. Tasks without a due date do not appear. Done tasks are excluded.

Each task shows a complete button, title, due-date badge, project badge (if assigned), and recurrence indicator.

---

## Projects Views

### `GET /projects`

Lists all non-archived projects. Each project shows:

- Project name (links to detail page)
- Description (if present)
- Open task count (all non-done tasks)
- Due-today task count (if any)

### `GET /projects/{project_id}`

Shows project metadata and all tasks assigned to that project, grouped by task status:

- Inbox, Next Action, Waiting For, Scheduled, Someday / Maybe, Done

Each group appears as a section heading followed by its tasks. Includes a quick-add form scoped to the project.

Returns 404 if the project does not exist.

---

## All Tasks View

### `GET /tasks`

Displays all tasks with optional filtering and text search. Supports the following query parameters:

| Parameter | Values | Description |
|---|---|---|
| `q` | free text | Case-insensitive search across title and notes |
| `status` | `inbox`, `next_action`, `waiting_for`, `scheduled`, `someday_maybe`, `done` | Filter by exact task status |
| `project_id` | integer or `none` | Filter by project ID; use `none` for tasks without a project |
| `has_due_date` | `yes`, `no` | Filter by presence or absence of a due date |
| `is_recurring` | `yes`, `no` | Filter by recurring flag |

All parameters are optional and can be combined. Invalid `status` values are ignored (all tasks are returned).

Each task shows:

- Complete button (for non-done tasks)
- Title
- Status badge with per-status color
- Due-date badge (color-coded: overdue in red, due today in blue)
- Project badge (if assigned)
- Recurrence indicator (if recurring)
- Rendered Markdown notes (if present)

Visual CSS classes applied to task items:

- `.task-overdue` — task is overdue (due_date before today, not done)
- `.task-due-today` — task is due today (not done)
- `.task-done` — task status is done
- `.task-inbox` — task status is inbox

Example request: `GET /tasks?status=inbox&q=groceries&has_due_date=yes`

---

## Error Handling

The application returns custom HTML error pages for common HTTP errors:

- **404 Not Found**: Rendered as a branded HTML page with navigation links back to Inbox, Today, Projects, and All Tasks.
- **500 Internal Server Error**: Rendered as a branded HTML page. The underlying error is logged server-side for diagnosis.

All errors are logged using structured logging (see Logging below).

---

## Logging

The application uses Python's standard `logging` module with a structured format:

```
2026-03-17T10:30:00+0000 INFO     app  GET /inbox 200 12.3ms
```

Log output includes:

- Timestamp in ISO 8601 format
- Log level
- Logger name (`app`)
- Message (request method, path, status code, and latency for HTTP requests)

Lifecycle events (startup, shutdown, database initialisation) and export actions are also logged.

---

## Export Endpoints

### `GET /export/tasks.csv`

Returns all tasks as a CSV file. Accepts an optional `status` query parameter to filter by task status.

Response headers:

- `Content-Type: text/csv`
- `Content-Disposition: attachment; filename=tasks-YYYY-MM-DD.csv`

CSV columns: `id`, `title`, `notes`, `status`, `due_date`, `is_recurring`, `recurrence_type`, `recurrence_interval_days`, `last_completed_at`, `project_id`, `created_at`, `updated_at`, `completed_at`.

### `GET /export/tasks.json`

Returns all tasks as a JSON array. Accepts an optional `status` query parameter.

Response headers:

- `Content-Type: application/json`
- `Content-Disposition: attachment; filename=tasks-YYYY-MM-DD.json`

### `GET /export/projects.csv`

Returns all projects as a CSV file.

CSV columns: `id`, `name`, `description`, `created_at`, `updated_at`, `archived_at`.

### `GET /export/projects.json`

Returns all projects as a JSON array.

---

## Backup and Data Persistence

### Database Location

The SQLite database file lives at the path defined by the `DATABASE_URL` environment variable. In Docker, the default is `/data/todo.db`, mounted as a named volume.

### Backup Procedure

SQLite is a single file. To back up the database:

1. **Copy the file while the app is running** (SQLite supports safe reads during writes):

   ```bash
   # Docker: copy from the named volume
   docker compose cp todo-app:/data/todo.db ./backup-todo.db

   # Local development
   cp ./data/todo.db ./backup-todo.db
   ```

2. **Use the export endpoints** for a portable, human-readable backup:

   ```bash
   curl -o tasks.csv http://localhost:8080/export/tasks.csv
   curl -o tasks.json http://localhost:8080/export/tasks.json
   curl -o projects.csv http://localhost:8080/export/projects.csv
   curl -o projects.json http://localhost:8080/export/projects.json
   ```

### Restore

Copy the backup into the container and restart:

```bash
docker compose down
docker compose cp ./backup-todo.db todo-app:/data/todo.db
docker compose up
```

If the container is not available for `docker compose cp`, copy directly into the named volume:

```bash
# Find the volume mount point
docker volume inspect mysimpletodos_todo_app_data --format '{{ .Mountpoint }}'

# Copy (may require sudo on Linux)
sudo cp ./backup-todo.db "$(docker volume inspect mysimpletodos_todo_app_data --format '{{ .Mountpoint }}')/todo.db"
```