---
name: todo-api
description: Interacting with the running MySimpleTodos app over HTTP — routes, endpoints, filtering, exports, and error handling.
---
# TODO API Skill

Use this skill when interacting with the running MySimpleTodos application over HTTP.

## Base Assumptions

- Local Docker Compose URL: `http://localhost:8080`
- Health endpoint: `GET /health`
- Landing page redirects to: `GET /inbox`

## Startup Checklist

1. Start the app with `docker compose up --build` or `uvicorn app.main:app --reload --host 0.0.0.0 --port 8080`.
2. Verify reachability with `GET /health`.
3. Expect JSON `{"status": "ok"}` from the health route.

## Page Routes

- `GET /` redirects to `/inbox`.
- `GET /inbox` shows inbox tasks with a quick-add form.
- `GET /today` shows overdue tasks and tasks due today (excludes done tasks and tasks without due dates).
- `GET /projects` lists non-archived, non-completed projects with open and due-today task counts.
- `GET /projects/{project_id}` shows project details with tasks grouped by status.
- `GET /projects/{project_id}/edit` shows the project edit form (name, description, notes, due_date).
- `GET /tasks` shows all tasks with filtering and search support.
- `GET /tasks/{task_id}/edit` shows the task edit form. Accepts optional `back_url` query parameter to preserve navigation context.

## Mutation Routes

### Tasks

- `POST /tasks` creates a task (form fields: `title`, optional `project_id`). Redirects back to the referring page.
- `POST /tasks/{task_id}/update` updates a task from the edit form. If `action=close` is passed, redirects back to the referring page (via `back_url`). Otherwise redirects back to the edit form.
- `POST /tasks/{task_id}/quick-update` inline single-field update (form fields: `field` plus the field value). Used for HTMX partial updates of `status`, `due_date`, or `project_id`. Redirects back to the referring page.
- `POST /tasks/{task_id}/complete` completes a task. Redirects back to the referring page.
- `POST /tasks/{task_id}/reopen` reopens a task to inbox. Redirects back to the referring page.

### Projects

- `POST /projects` creates a project (form field: `name`). Redirects to `/projects`.
- `POST /projects/{project_id}/update` updates project metadata (form fields: `name`, `description`, `notes`, `due_date`, `action`, `back_url`). Redirects based on `action`.
- `POST /projects/{project_id}/complete` marks a project complete (only when all tasks are done). Redirects back to the referring page.

See `docs/api.md` for full form field specifications.

## All Tasks Filtering and Search

The `GET /tasks` page accepts query parameters:

| Parameter | Values | Meaning |
|---|---|---|
| `q` | free text | Case-insensitive search across title and notes |
| `status` | `all_in_work` (default), `inbox`, `next_action`, `waiting_for`, `scheduled`, `someday_maybe`, `done` | Exact status match; `all_in_work` shows all non-done tasks |
| `project_id` | integer or `none` | Filter by project; `none` for unassigned |
| `has_due_date` | `yes`, `no` | Has or lacks a due date |
| `is_recurring` | `yes`, `no` | Recurring or non-recurring |

Parameters combine with AND logic. Example: `/tasks?status=inbox&q=groceries`

## Today View Behavior

The Today page shows two sections:
1. **Overdue**: tasks with `due_date` before today, status not `done`.
2. **Due Today**: tasks with `due_date` equal to today, status not `done`.

Recurring tasks whose next due date is today appear automatically. Tasks without due dates are excluded.

## Project Views Behavior

- The projects list shows all non-archived, non-completed projects with open task counts and due-today counts.
- The project detail page groups tasks by status (Inbox, Next Action, Waiting For, Scheduled, Someday / Maybe, Done).
- A quick-add form on the project detail page creates tasks pre-assigned to that project.
- The project edit page allows editing name, description, notes (Markdown), and due_date.
- Projects can be marked complete when all their tasks are done.

## Visual Distinction

Tasks have CSS classes that indicate their state for any UI interaction or scraping:

- `.task-overdue` — overdue (due_date < today, not done)
- `.task-due-today` — due today (not done)
- `.task-done` — completed
- `.task-inbox` — inbox status

## Export Routes

- `GET /export/tasks.csv` — all tasks as CSV. Optional `status` query parameter.
- `GET /export/tasks.json` — all tasks as JSON. Optional `status` query parameter.
- `GET /export/projects.csv` — all projects as CSV (includes notes, due_date, completed_at).
- `GET /export/projects.json` — all projects as JSON (includes notes, due_date, completed_at).

All export responses include a `Content-Disposition` header with a date-stamped filename.

## Error Handling

- 404 errors return a branded HTML page with navigation links.
- 500 errors return a branded HTML page; the error is logged server-side.
- All requests are logged with method, path, status code, and latency.

## Logging

Structured logging to stdout: `YYYY-MM-DDTHH:MM:SS LEVEL app MESSAGE`.
Startup, shutdown, database init, exports, and errors are all logged.

## Backup

The SQLite file at `/data/todo.db` (Docker) can be backed up by:

1. Copying the file: `docker compose cp todo-app:/data/todo.db ./backup.db`
2. Using the export endpoints for CSV/JSON dumps.

See `docs/api.md` for full backup and restore procedures.

## General Conventions

- HTML page routes return server-rendered responses.
- Mutation routes accept form-encoded POST data and redirect on success.
- Not-found resources return HTTP 404 with a branded error page.
- Empty titles are rejected on update (redirect back to edit form).
- SQLite persistence uses the database URL configured in `DATABASE_URL`.

## Authentication

All routes except `/health`, `/auth/*`, and `/static/*` require an authenticated session when `AUTH_DISABLED` is not `true`.

### Auth Routes

- `GET /auth/setup` — first-run passkey registration page (only when no credentials exist).
- `POST /auth/setup/options` — returns WebAuthn `PublicKeyCredentialCreationOptions` JSON.
- `POST /auth/setup/verify` — verifies registration, stores credential, sets session cookie. Accepts JSON body.
- `GET /auth/login` — login page (redirects to `/auth/setup` if no credentials exist).
- `POST /auth/login/options` — returns WebAuthn `PublicKeyCredentialRequestOptions` JSON.
- `POST /auth/login/verify` — verifies authentication, updates sign count, sets session cookie. Accepts JSON body.
- `POST /auth/logout` — clears session cookie, redirects to `/auth/login`.

### Session Cookie

- Name: `mst_session`
- Signed with `itsdangerous.TimestampSigner`
- `HttpOnly`, `SameSite=Lax`, `Secure` (when HTTPS origin)
- Max age: `AUTH_SESSION_MAX_AGE` environment variable (default 7 days)

### Auth Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `AUTH_DISABLED` | `false` | Skip auth entirely |
| `AUTH_SECRET_KEY` | auto-generated | Secret for signing cookies |
| `AUTH_SESSION_MAX_AGE` | `604800` | Cookie max age (seconds) |
| `WEBAUTHN_RP_ID` | `localhost` | WebAuthn Relying Party ID |
| `WEBAUTHN_RP_NAME` | `MySimpleTodos` | RP display name |
| `WEBAUTHN_ORIGIN` | `http://localhost:8080` | Expected origin |

### API Key (Programmatic Access)

API keys allow CLI tools and scripts to access the API without a browser session.

Include the key in the `Authorization` header:

```
Authorization: Bearer mst_your_key_here
```

API keys grant access to all protected routes (same scope as session cookies).

### Managing API Keys

- `GET /settings` — Settings page with API key management (requires session cookie)
- `POST /settings/api-keys` — Generate a new key (requires session, form field: `name`)
- `POST /settings/api-keys/{key_id}/revoke` — Revoke a key (requires session)

Keys are shown once at creation. Up to 10 active keys. Keys are stored as SHA-256 hashes.

**Important:** API key management requires a session cookie. API keys cannot be used to create or revoke other keys.

### Bypassing Auth in Tests

Set `AUTH_DISABLED=true` in the environment. The test `conftest.py` does this by default.

## Troubleshooting

- If the app is unreachable, confirm the container or local process is running.
- If database startup fails, verify that the SQLite target directory is writable.
- Check application logs (stdout) for structured error messages.
- If behavior changes, update `docs/api.md` and this skill file together.