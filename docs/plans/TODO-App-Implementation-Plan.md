# TODO App — Implementation Plan

_March 2026_

## Architectural Decisions (Fixed)

These decisions are fixed to keep the application simple, local-first, and easy to operate on a laptop.

| Decision | Choice |
|---|---|
| **Primary user experience** | Simple web app for local use in a browser |
| **Framework style** | Server-rendered UI with small HTMX interactions |
| **Backend stack** | Python 3.12 + FastAPI |
| **Frontend stack** | Jinja templates + HTMX + minimal vanilla JavaScript |
| **Database** | SQLite |
| **ORM / data access** | SQLModel or SQLAlchemy |
| **Containerization** | Single Docker image |
| **Local deployment** | Docker Compose with one app service and one mounted data volume |
| **Auth** | None for MVP when running locally on a laptop |
| **Scope model** | GTD-inspired tasks, projects, inbox, next actions, waiting, scheduled, someday, done |
| **Task notes format** | Markdown stored as text and rendered safely to HTML |
| **LLM customization assets** | Repository-scoped skills and instructions under `.github/` |
| **CI/CD** | GitHub Actions on every push and pull request |
| **Development methodology** | Test-driven development in every phase |

---

## Phase Structure Rationale

The phases are intentionally scoped for an LLM-based delivery flow where each phase ends in a commit-ready state and the next phase starts in a new conversation.

### Design Rules for Every Phase

1. Each phase must fit comfortably within a fresh conversation without requiring the model to reload deep implementation detail from all earlier phases
2. Each phase must end with working code, passing tests, and updated documentation for the surfaces touched in that phase
3. Each phase must preserve a stable public surface for the next phase, so the next conversation can work primarily from documented interfaces and current code rather than project memory
4. Each phase must be test-first: write or update failing tests, implement until green, then commit

### Why This Matters for LLM-Based Development

- Smaller, dependency-ordered phases reduce the chance of blowing up the context window
- Commit-ready outputs create a clean restart point for the next conversation
- TDD provides an executable specification that a new conversation can trust when extending the system
- Documentation and `.github` assets reduce rediscovery work for future agent sessions

### Rule for Every Phase

- Start by reading only the current phase's relevant code, tests, and docs
- Add or update tests first
- Implement only the minimum code needed to pass those tests
- Update `README.md`, `docs/`, and `.github` assets if behavior or interfaces changed
- Ensure CI passes before considering the phase complete

---

## How to Use This Plan as the Sole Build Brief

If this document is handed to Copilot as the only project brief for an empty GitHub repository, the agent should follow these rules:

1. Treat the architectural decisions in this document as binding unless they conflict with the repository's actual code
2. Start with Phase 0 only; do not jump ahead to later phases in the same implementation pass
3. Create the repo structure exactly or very close to the structure defined for Phase 0
4. Use TDD for every new capability, beginning with the tests named in the relevant phase
5. Keep all outputs commit-ready at the end of each phase
6. Update `README.md`, `docs/`, `.github/copilot-instructions.md`, and the skill files whenever external behavior changes
7. Prefer the simplest implementation that satisfies the stated acceptance criteria
8. Do not add extra product scope that is not named in this plan

### Priority Order When Tradeoffs Appear

If a coding agent has to choose between multiple valid implementations, use this priority order:

1. Passing tests and stable behavior
2. Simplicity of the codebase
3. Clear documentation and agent discoverability
4. Local operability in Docker
5. UI polish

### Non-Negotiable Constraints for Any Implementation Agent

- The project must remain runnable on a laptop using Docker Compose
- SQLite must remain the persistent database for MVP
- Recurring tasks must remain single-record tasks whose `due_date` advances on completion
- Task notes must remain raw Markdown in storage and safe HTML in display
- The repository must keep `.github` skills and instructions in sync with actual behavior
- CI must run on every push and pull request

---

## Product Goal

Build a lightweight TODO application that supports the Getting Things Done framework while staying intentionally small:

1. Capture items quickly
2. Organize tasks under projects
3. Track an optional due date for each task
4. Support repeating tasks for recurring commitments
5. Store task notes with Markdown support for richer context
6. Show a dedicated view for items due today
7. Show all tasks for a selected project
8. Run entirely on a laptop in Docker with persistent local storage
9. Include repo-scoped LLM skills so an assistant can interface with the app programmatically

---

## MVP Scope

### Core User Flows

1. Create a task with title, Markdown notes, optional due date, GTD status, optional project, and optional recurrence rule
2. Edit or complete a task
3. Create and rename projects
4. View all open tasks for a project
5. View all tasks due today
6. View inbox items that are not yet organized
7. Move tasks between GTD states

### Explicitly In Scope

- Project-based organization
- Optional due dates
- Recurring tasks
- Markdown notes
- GTD state tracking
- Simple filtering and sorting
- Persistent SQLite storage
- Dockerized local deployment
- Repo-level `.github` skills and instructions for LLM interaction

### Explicitly Out of Scope for MVP

- Multi-user support
- Cloud sync
- Mobile app
- Email integration
- Attachments
- Notifications beyond an in-app due-today view

---

## GTD Model

The application should map tasks into a practical GTD structure without overcomplicating capture and review.

### Task States

| State | Meaning |
|---|---|
| **inbox** | Captured but not yet clarified |
| **next_action** | Ready to do next |
| **waiting_for** | Blocked on someone or something else |
| **scheduled** | Has a due date or is intended for later |
| **someday_maybe** | Deferred without commitment |
| **done** | Completed |

### Project Definition

A project is any desired outcome that requires more than one task. A project page should show:

- Project name and description
- Open tasks grouped by GTD state
- Completed tasks in a collapsible section
- Counts for total open, due today, and overdue items

### Due Date Semantics

- Due date is optional
- If a due date equals the current local date, the item appears in the Today view
- Overdue items should be visually distinct from due-today items
- Tasks without due dates should still be valid GTD items

### Recurrence Semantics

- Recurrence is optional and configured per task
- MVP recurrence patterns: daily, weekly, monthly, and custom interval in days
- Recurring tasks use a single persistent task record; the app does not generate separate task instances
- Completing a recurring task advances that same task's `due_date` to the next occurrence while preserving recurrence settings and notes
- Non-recurring tasks move to `done`; recurring tasks are considered complete for the current cycle and immediately rescheduled for the next cycle
- The Today view should include recurring tasks whose next due date is today
- The completion action should update `last_completed_at` and `updated_at` so the app still retains a basic audit trail without introducing child instances

### Notes Semantics

- Task notes support Markdown input for richer context
- Notes are stored as raw Markdown text in the database
- Markdown is rendered to safe HTML on display using sanitization to prevent unsafe content
- Plain text notes remain valid Markdown and require no migration path

---

## Recommended System Design

### Why This Stack

For a personal laptop-hosted application, the main engineering goal is low operational overhead. FastAPI plus server-rendered templates avoids the complexity of a separate frontend build pipeline while still allowing dynamic interactions through HTMX. SQLite keeps the data layer simple, portable, and easy to back up.

### High-Level Architecture

```text
Browser
  -> FastAPI application
      -> Jinja templates / HTMX partials
      -> Service layer
      -> SQLite database file
      -> Local Docker volume for persistence
```

### Deployment Topology

```text
Docker Compose
  -> todo-app container
      - FastAPI web server
      - app code
      - SQLite client access
      - mounted /data volume

Host machine
  -> persistent SQLite file stored in mounted volume
```

### LLM Interface Strategy

The repository should include agent customization assets so an LLM can reliably discover how to use the application without reverse-engineering the codebase. These assets should live in `.github/` and be treated as part of the delivered product, not as optional documentation.

Recommended assets:

- `.github/copilot-instructions.md` for always-on project conventions
- `.github/skills/todo-api/SKILL.md` for programmatic interaction with the HTTP interface
- `.github/skills/todo-data-model/SKILL.md` for task, project, recurrence, and Markdown-note semantics
- `.github/workflows/ci.yml` for push and pull-request validation
- `.github/prompts/` entries only if repeated one-shot tasks become useful later

The initial skills should teach an LLM how to:

1. Start the app locally with Docker Compose
2. Call the app's HTTP endpoints correctly
3. Create, update, complete, and query tasks
4. Work with recurring-task semantics using the single-record model
5. Submit and interpret Markdown notes safely

---

## Bootstrap Specification for an Empty GitHub Repo

This section is intended to remove ambiguity if the project is started from a completely empty repository. A coding agent should be able to use this document alone to begin implementation.

### Initial Tooling Choices

Use the following concrete choices unless a later phase explicitly changes them:

| Area | Choice |
|---|---|
| **Python packaging** | `pyproject.toml` with `setuptools` build backend |
| **Dependency installation** | `pip install -e .[dev]` |
| **Test runner** | `pytest` |
| **Async HTTP testing** | `httpx` test client |
| **Linting / formatting** | `ruff` |
| **Static typing** | `mypy` |
| **Database migrations** | `alembic` |
| **Template engine** | `jinja2` |
| **Form handling** | `python-multipart` |
| **Markdown rendering** | `markdown-it-py` |
| **HTML sanitization** | `bleach` |
| **ASGI server** | `uvicorn[standard]` |

### Initial Runtime Dependencies

- `fastapi`
- `uvicorn[standard]`
- `sqlmodel`
- `alembic`
- `jinja2`
- `python-multipart`
- `markdown-it-py`
- `bleach`

### Initial Development Dependencies

- `pytest`
- `pytest-cov`
- `httpx`
- `mypy`
- `ruff`

### Global Conventions

- Keep the application importable as the `app` package
- Prefer synchronous SQLModel access for MVP simplicity unless async behavior becomes necessary later
- Keep HTML rendering server-side by default; only add client-side JavaScript where HTMX or form enhancement clearly reduces complexity
- Use UTC timestamps for `created_at`, `updated_at`, `completed_at`, and `last_completed_at`
- Use local-date comparison for `due_date` behavior in the Today view
- Keep environment configuration in one place, such as `app/config.py`
- Keep database session setup in one place, such as `app/db.py`
- Do not add authentication or user accounts in MVP

### Definition of Done for Any Phase

A phase is only complete when all of the following are true:

1. New tests were written first and now pass
2. Existing tests still pass
3. Lint and type checks pass
4. Docker build still succeeds
5. README and relevant docs reflect the new behavior
6. `.github` guidance is updated if programmatic behavior or workflow changed
7. The output is commit-ready and can be picked up by a new conversation without hidden context

---

## Data Model

Two primary entities are enough for MVP: projects and tasks.

### `projects` Table

| Column | Type | Notes |
|---|---|---|
| `id` | integer | Primary key |
| `name` | text | Required, unique |
| `description` | text | Optional |
| `created_at` | datetime | Required |
| `updated_at` | datetime | Required |
| `archived_at` | datetime | Optional |

### `tasks` Table

| Column | Type | Notes |
|---|---|---|
| `id` | integer | Primary key |
| `title` | text | Required |
| `notes` | text | Optional raw Markdown |
| `status` | text | Enum-like string: `inbox`, `next_action`, `waiting_for`, `scheduled`, `someday_maybe`, `done` |
| `due_date` | date | Optional |
| `is_recurring` | boolean | Required, default false |
| `recurrence_type` | text | Optional: `daily`, `weekly`, `monthly`, `interval_days` |
| `recurrence_interval_days` | integer | Optional, used when `recurrence_type = interval_days` |
| `last_completed_at` | datetime | Optional |
| `project_id` | integer | Nullable foreign key to `projects.id` |
| `created_at` | datetime | Required |
| `updated_at` | datetime | Required |
| `completed_at` | datetime | Optional |

### Recurring Task Behavior in Storage

- A recurring task remains a single row in `tasks`
- `due_date` always represents the next active due date for that task
- `last_completed_at` records when the previous cycle was completed
- `completed_at` is only used for non-recurring tasks that are actually done and closed out
- `status` should typically remain actionable for recurring tasks after rescheduling, rather than moving permanently to `done`

### Useful Indexes

- Index on `tasks.due_date`
- Index on `tasks.project_id`
- Index on `tasks.status`
- Index on `tasks.is_recurring`
- Composite index on `tasks.project_id, status`

### Future-Safe Additions

These should not be in MVP unless needed during implementation:

- `contexts` table for GTD contexts such as `@home` or `@computer`
- `reviewed_at` field for weekly review workflows
- `priority` field
- subtask support

---

## Application Views

### 1. Inbox

Purpose: rapid capture and triage.

Features:
- Quick-add form
- List of tasks with status `inbox`
- Inline controls to assign project, due date, recurrence, notes, and state

### 2. Today

Purpose: show the work with a due date equal to the current date.

Features:
- Tasks due today across all projects
- Overdue section above due-today section
- Recurring tasks due today shown alongside one-time tasks
- Completion toggle
- Link back to the owning project if assigned

### 3. Projects List

Purpose: browse active projects.

Features:
- List all non-archived projects
- Show counts for open tasks and due-today tasks
- Button to create a new project

### 4. Project Detail

Purpose: view all items under a project.

Features:
- Project metadata
- Tasks grouped by GTD state
- Sort by due date, then creation date
- Render Markdown notes safely within task detail or expanded task rows
- Quick-add task directly into the project

### 5. All Tasks

Purpose: full list for search and review.

Features:
- Filter by state
- Filter by project
- Filter by due-date presence
- Filter by recurring vs non-recurring
- Search by title or notes

---

## API / Route Design

The app can stay simple with a mix of HTML page routes and a few form-post endpoints.

### Page Routes

- `GET /` -> redirect to Inbox or Today
- `GET /inbox` -> inbox page
- `GET /today` -> due-today page
- `GET /projects` -> projects list
- `GET /projects/{project_id}` -> project detail
- `GET /tasks` -> all tasks page

### Mutation Routes

- `POST /tasks` -> create task
- `POST /tasks/{task_id}/update` -> edit title, notes, due date, project, status
- `POST /tasks/{task_id}/complete` -> mark complete; if recurring, advance `due_date` on the same record instead of closing the task
- `POST /tasks/{task_id}/reopen` -> reopen task
- `POST /projects` -> create project
- `POST /projects/{project_id}/update` -> rename or edit project
- `POST /projects/{project_id}/archive` -> archive project

If an API-first frontend is desired later, these routes can be mirrored with JSON endpoints under `/api`.

---

## Docker and Persistence Plan

### Container Strategy

Use one container for the web app. SQLite lives in a mounted host-backed volume so that container rebuilds do not lose data.

### Files to Include

```text
todo-app/
├── .github/
│   ├── copilot-instructions.md
│   ├── workflows/
│   │   └── ci.yml
│   └── skills/
│       ├── todo-api/
│       │   └── SKILL.md
│       └── todo-data-model/
│           └── SKILL.md
├── app/
│   ├── main.py
│   ├── models.py
│   ├── routes/
│   ├── services/
│   ├── templates/
│   ├── static/
│   └── db.py
├── tests/
├── docs/
│   ├── api.md
│   └── llm-integration.md
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

### Dockerfile Requirements

- Use a slim Python base image
- Install Python dependencies
- Copy application code
- Expose the app port
- Start FastAPI with Uvicorn

### `docker-compose.yml` Requirements

- One `todo-app` service
- Bind a local port such as `8080:8080`
- Mount a named volume or bind mount to `/data`
- Pass database path through environment variable such as `DATABASE_URL=sqlite:////data/todo.db`

### Operational Commands

```bash
docker compose up --build
docker compose down
docker compose exec todo-app python -m app.seed
```

---

## LLM-Facing Repository Assets

### `.github/copilot-instructions.md`

Purpose: define always-on project guidance for agents working in the repository.

Should include:

- Preferred commands for local startup and testing
- The requirement that all feature work follows TDD
- The canonical database location and persistence model
- The rule that recurring tasks use a single persistent record
- The rule that notes are stored as Markdown and rendered safely
- Pointers to API docs and skill files

### `.github/workflows/ci.yml`

Purpose: run the same validation locally expected for every checkin on GitHub.

Should include:

- Trigger on every push and pull request
- Test job for the Python test suite
- Lint or static-check job for Python code and templates where practical
- Docker build validation so container regressions are caught early
- Documentation validation for any machine-consumed `.github` and `docs/` assets where practical

### `.github/skills/todo-api/SKILL.md`

Purpose: teach an LLM how to programmatically interact with the running application.

Should include:

- Base URL assumptions for local Docker deployment
- Supported HTTP routes and expected payloads
- Examples for creating tasks and projects
- Examples for completing recurring and non-recurring tasks
- Error handling expectations
- Common troubleshooting steps when the app is not reachable

### `.github/skills/todo-data-model/SKILL.md`

Purpose: teach an LLM the domain semantics so it behaves correctly when reading or writing task data.

Should include:

- Definitions of GTD statuses
- Project semantics
- Due-date semantics
- Single-record recurrence semantics
- Markdown notes behavior and sanitization expectations

### Supporting Docs

The skill files should reference human-readable docs that are maintained alongside the code:

- `README.md` for startup and developer workflow
- `docs/api.md` for route definitions and payload examples
- `docs/llm-integration.md` for a compact guide to how agents should interface with the app

---

## Implementation Phases

## Phase 0: Bootstrap

**Goal:** Create a working project skeleton, initial `.github` infrastructure, GitHub CI, and a containerized local run path.

### Phase 0 Repository Structure

Phase 0 should create the following repository layout.

```text
todo-app/
├── .github/
│   ├── copilot-instructions.md
│   ├── workflows/
│   │   └── ci.yml
│   └── skills/
│       ├── todo-api/
│       │   └── SKILL.md
│       └── todo-data-model/
│           └── SKILL.md
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── db.py
│   ├── models.py
│   ├── schemas.py
│   ├── markdown.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── pages.py
│   │   └── health.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── health_service.py
│   ├── templates/
│   │   ├── base.html
│   │   └── index.html
│   └── static/
│       └── app.css
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_health.py
│   ├── test_app_boot.py
│   └── test_pages.py
├── docs/
│   ├── api.md
│   └── llm-integration.md
├── scripts/
│   └── bootstrap.sh
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .gitignore
├── .env.example
├── README.md
└── alembic.ini
```

### Purpose of Key Phase 0 Files

| File | Purpose |
|---|---|
| `pyproject.toml` | Python project metadata, dependencies, and tool configuration |
| `.github/workflows/ci.yml` | CI checks on push and pull request |
| `.github/copilot-instructions.md` | Always-on repo guidance for Copilot |
| `.github/skills/todo-api/SKILL.md` | Programmatic interface guidance for agents |
| `.github/skills/todo-data-model/SKILL.md` | GTD, recurrence, and Markdown semantics for agents |
| `app/main.py` | FastAPI app creation and route registration |
| `app/config.py` | Environment-driven settings such as database path and host/port |
| `app/db.py` | SQLite engine and session wiring |
| `app/routes/health.py` | Health endpoint used by tests and container checks |
| `tests/` | Test-first enforcement for Phase 0 and future phases |
| `docs/api.md` | Starts as a stub and grows with actual routes |
| `docs/llm-integration.md` | Compact guide for agent-driven usage |

### Phase 0 Required Tool Configuration

`pyproject.toml` should include at least:

- Project metadata and package discovery for `app`
- Runtime dependencies listed in this plan
- Optional `dev` dependency group for test, lint, and type-check tools
- `ruff` configuration
- `mypy` configuration
- `pytest` configuration with `testpaths = ["tests"]`

### Phase 0 Required CI Pipeline

`ci.yml` should run the following jobs on every push and pull request:

1. Install Python and project dependencies
2. Run `ruff check .`
3. Run `mypy app`
4. Run `pytest`
5. Run `docker build .`

If practical in Phase 0, also run a container smoke check after build. If that is too heavy for initial bootstrap, it can be deferred to Phase 1 as long as `docker build` is in place immediately.

### Phase 0 Required `.github/copilot-instructions.md` Content

The file should include:

- The requirement to work phase-by-phase using TDD
- The rule that new conversations should rely on code, tests, docs, and `.github` assets rather than prior chat history
- Canonical local commands for install, test, lint, type-check, Docker build, and Docker Compose startup
- The architectural constraints from this plan: FastAPI, SQLite, server-rendered UI, single-record recurring tasks, Markdown notes with sanitization
- The expectation that API and skill docs stay synchronized with behavior

### Phase 0 Required Initial Tests

Phase 0 is not just scaffolding. It must begin with executable tests.

Required tests:

1. App factory or app import succeeds
2. `GET /health` returns `200` and a simple JSON payload such as `{ "status": "ok" }`
3. `GET /` returns `200` or a documented redirect response
4. Template rendering works for the initial landing page
5. Database engine initializes against a local SQLite path

### Phase 0 Required Docker Behavior

- `Dockerfile` must build successfully from the repo root
- `docker-compose.yml` must define one `todo-app` service
- The app must listen on port `8080` in the container
- Compose should expose `8080:8080`
- Compose should mount a persistent volume to `/data`
- Default database URL should point to a SQLite file under `/data`

### Phase 0 Deliverable Quality Bar

Phase 0 should be a complete bootstrap that a new conversation can pick up without further architecture work. That means no placeholder files that only say "TODO" unless they are accompanied by working tests and clearly defined next-step interfaces.

### Deliverables

- FastAPI app starts locally and in Docker
- Basic folder structure in place
- SQLite connection configured
- Health check endpoint added
- Markdown rendering library and HTML sanitization dependency selected
- `.github/copilot-instructions.md` created with project-wide agent guidance
- `.github/skills/todo-api/SKILL.md` created as an initial stub with startup and endpoint conventions
- `.github/skills/todo-data-model/SKILL.md` created as an initial stub with GTD, recurrence, and notes semantics
- `.github/workflows/ci.yml` created to run on every push and pull request
- Test framework, linting, and local test command wired into the repo
- Initial tests for app startup, health check, and container boot path
- README with local run instructions

### Phase 0 README Requirements

The initial `README.md` should contain:

1. One-paragraph description of the app and its MVP scope
2. Local Python setup instructions
3. Local Docker Compose startup instructions
4. Test, lint, and type-check commands
5. Short description of the project structure
6. Link references to `docs/api.md`, `docs/llm-integration.md`, and `.github/skills/`

### Acceptance Criteria

- `docker compose up --build` starts the app successfully
- Visiting the root page in a browser returns a valid HTML page
- SQLite database file is created in mounted storage
- Repository contains baseline `.github` customization files for agent discovery
- GitHub Actions is configured to run on every push and pull request
- The initial test suite passes locally and in CI
- Phase 0 can be committed independently without relying on later phases

### Phase 0 Handoff Contract for the Next Conversation

At the end of Phase 0, the repository must make the next phase obvious. Specifically:

- The app boots
- CI is active
- Tests exist and are passing
- The route, config, and database entry points are easy to find
- `.github` guidance exists for future agent work
- The next phase can focus on data modeling rather than bootstrap decisions

---

## Phase 1: Database and Domain Model

**Goal:** Implement durable storage for projects and tasks.

### Deliverables

- `projects` and `tasks` models
- Schema creation or migration setup
- Repository or service layer for CRUD operations
- Recurrence rule persistence and single-record due-date advancement logic
- `docs/api.md` skeleton with request and response examples
- Seed data for local testing

### TDD Expectations

- Add model and service tests before implementing schema or persistence logic
- Keep Phase 1 limited to domain and storage concerns so the next phase can focus on UI flows

### Acceptance Criteria

- Tasks can be created, updated, and completed
- Projects can be created and linked to tasks
- Due dates persist correctly
- Recurring tasks advance the same record correctly on completion
- Markdown notes persist exactly as entered

---

## Phase 2: Core GTD Workflows

**Goal:** Enable capture, clarification, and organization.

### Deliverables

- Inbox page
- Quick task capture form
- Edit form for status, due date, recurrence, Markdown notes, and project assignment
- Completion and reopen actions

### TDD Expectations

- Write route and form-submission tests before implementing each workflow
- Keep this phase focused on the inbox and task lifecycle so it remains small enough for a single conversation

### Acceptance Criteria

- New tasks default to `inbox`
- Tasks can move into `next_action`, `waiting_for`, `scheduled`, `someday_maybe`, and `done`
- Tasks can optionally remain unassigned to a project
- Recurring tasks can be created and completed without losing their recurrence settings or record identity
- Markdown notes render safely in the UI

---

## Phase 3: Today and Project Views

**Goal:** Deliver the two most important user views from the requirements.

### Deliverables

- Today page with due-today and overdue sections
- Projects list page
- Project detail page showing all tasks under a project
- `docs/api.md` expanded to cover the routes exercised by these views
- `.github/skills/todo-api/SKILL.md` updated to reflect real route behavior

### TDD Expectations

- Add page-level tests for due-today, overdue, and project-grouped task rendering before implementation
- Keep scope restricted to read and display flows, not broad filtering or polish

### Acceptance Criteria

- A task due today appears in Today automatically
- A recurring task whose next due date is today appears in Today automatically
- A task assigned to a project appears on that project's page
- Project page displays all non-archived tasks for that project grouped by status

---

## Phase 4: Filtering, Search, and UX Polish

**Goal:** Make the app practical for daily use.

### Deliverables

- All Tasks page with filters
- Search by task title and notes
- Basic visual distinction for overdue, due today, done, and inbox items
- Markdown preview or clearly rendered notes view
- `docs/llm-integration.md` tying together routes, semantics, and local startup steps
- Empty states and validation messages

### TDD Expectations

- Add regression tests for filters, search, and Markdown rendering before implementing polish work
- Keep this phase limited to discoverability and usability improvements

### Acceptance Criteria

- Users can find tasks by project, status, or text search
- Overdue items are easy to distinguish from due-today items
- Invalid input is rejected with understandable feedback
- Markdown notes remain readable and safely rendered after edit cycles
- An LLM can discover how to start and call the app by reading `.github` assets and linked docs

---

## Phase 5: Hardening and Backup

**Goal:** Make the local deployment dependable.

### Deliverables

- Structured logging
- Error pages
- Backup guidance for SQLite file
- Optional export to CSV or JSON

### TDD Expectations

- Add tests for error handling, export paths, and backup-related commands or helpers where practical
- Keep this phase focused on operational quality rather than adding new product scope

### Acceptance Criteria

- App failures are diagnosable from logs
- Data file location is documented clearly
- User can back up the database without special tooling

---

## Testing Strategy

### Automated Tests

- Unit tests for task and project services
- Integration tests for page routes and form submissions
- Database tests against temporary SQLite files
- CI execution of the same core test suite on every push and pull request

### Testing Rule

Testing is not a cleanup activity at the end of a phase. Every phase starts by adding or adjusting tests that define the intended behavior for that phase.

### Key Behaviors to Test

1. Creating a task without a due date
2. Creating a task with a due date equal to today
3. Creating a recurring task with a weekly rule
4. Completing a recurring task and advancing its next due date on the same record
5. Assigning a task to a project
6. Moving a task from inbox to next action
7. Completing and reopening a non-recurring task
8. Rendering Markdown notes safely without unsafe HTML execution
9. Filtering project tasks correctly
10. Showing overdue items separately from due-today items
11. Keeping documented API examples consistent with actual route behavior

### Manual Smoke Tests

1. Start via Docker Compose
2. Create a project
3. Add four tasks: one due today, one overdue, one recurring weekly task due today, and one without due date
4. Add Markdown notes to at least one task
5. Confirm Today view and Project view behave correctly
6. Complete the recurring task and verify the same task remains visible with its next due date advanced
7. Restart the container and verify data persists
8. Follow the `.github` skill instructions to create and update a task programmatically

---

## Recommended Milestone Order

1. Bootstrap FastAPI app, Docker, `.github` infrastructure, GitHub Actions, and test harness
2. Implement task and project persistence, including recurrence fields
3. Build Inbox flow and Markdown-capable task editing
4. Build Today view, including recurring due-today logic
5. Build Project list and Project detail views
6. Add filtering, search, and UI cleanup
7. Add backup/export support

---

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| **Overbuilding the GTD model** | Keep MVP limited to tasks, projects, states, and due dates |
| **Recurring-task logic becoming inconsistent** | Use the single-record recurrence model only and cover due-date advancement with integration tests |
| **Unsafe Markdown rendering** | Sanitize rendered HTML and restrict supported extensions |
| **Frontend complexity creep** | Use server rendering with HTMX rather than a separate SPA |
| **SQLite file corruption or accidental loss** | Store DB on mounted volume and document backups clearly |
| **Date handling bugs** | Normalize all due-date comparisons to local date boundaries |
| **Docker-only debugging friction** | Keep local non-Docker run path available during development |
| **LLM instructions drifting from the implementation** | Keep `.github` skills versioned with the code and validate examples against integration tests |

---

## Success Criteria

The implementation is successful when all of the following are true:

1. The app runs locally in Docker on a laptop with persistent data
2. Tasks support an optional due date
3. Recurring tasks can be created and advance correctly on completion using the same task record
4. Task notes support Markdown and render safely
5. The Today view correctly shows due-today items
6. The user can open a project and see all tasks under that project
7. The app supports a practical GTD workflow without unnecessary complexity
8. A repo-scoped LLM can learn how to interface with the app by reading `.github` skills and linked docs

---

## Recommendation

Build this as a single-container FastAPI application backed by SQLite, with a server-rendered HTML interface enhanced by HTMX. Package the implementation with repo-scoped `.github` skills and concise API documentation so an LLM can reliably start the app, understand the GTD and recurrence semantics, and interact with the HTTP interface programmatically. That gives the lowest-effort path to a maintainable personal productivity tool while also making agent integration intentional rather than incidental.