# MySimpleTodos Copilot Instructions

## Working Model

- Implement one phase at a time from `docs/TODO-App-Implementation-Plan.md`.
- Follow test-driven development for every feature and change.
- Start a new conversation from current code, tests, docs, and `.github` assets instead of relying on previous chat history.

## Canonical Commands

Install development dependencies:

```bash
uv sync
```

Run the test suite:

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

Run the app locally:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

Build the image:

```bash
docker build .
```

Start the compose stack:

```bash
docker compose up --build
```

## Architecture Constraints

- Backend: FastAPI on Python 3.12.
- UI: server-rendered Jinja templates with small HTMX interactions when needed.
- Persistence: SQLite, with the canonical persistent path under `/data` in Docker.
- Authentication: Single-user passkey (WebAuthn) via `py_webauthn` and `itsdangerous` session cookies. API keys (`Authorization: Bearer mst_...`) provide programmatic access. Set `AUTH_DISABLED=true` to skip auth in dev/test. Existing tests use `AUTH_DISABLED=true` via `conftest.py`.
- Domain rule: recurring tasks remain single persistent task records whose `due_date` advances on completion.
- Notes rule: task notes are stored as raw Markdown and rendered as safe HTML.
- Responsive UI: the browser UI must remain usable without horizontal panning at viewport widths >= 320px. Use the three-tier breakpoint strategy (`sm` <= 599px, `md` 600–899px, `lg` >= 900px) defined in `docs/plans/Adaptive-Responsive-UX-Implementation-Plan.md`. Bottom-fixed elements must respect `env(safe-area-inset-bottom)`, and tap targets on `sm` must be >= 44x44 CSS px.

## Skills

Before starting work, read the relevant skill file from `.github/skills/`:

- **Daily Report** (`.github/skills/daily-report/SKILL.md`): When the user asks for a daily report, focus plan, tomorrow's priorities, or a task review.
- **TODO API** (`.github/skills/todo-api/SKILL.md`): When interacting with the running app over HTTP — routes, endpoints, filtering, exports, and error handling.
- **TODO Data Model** (`.github/skills/todo-data-model/SKILL.md`): When reasoning about task/project semantics — statuses, due dates, recurrence, and notes.
- **MST CLI** (`.github/skills/mst-cli/SKILL.md`): When using the command line to manage tasks, projects, or generate reports instead of the HTTP API directly.

## Documentation Expectations

- Keep `README.md`, `docs/`, and `.github/skills/` synchronized with behavior.
- Treat `.github` assets as part of the product surface for future agent sessions.