---
name: todo-data-model
description: Reasoning about task and project semantics — statuses, due dates, recurrence, and notes.
---
# TODO Data Model Skill

Use this skill when reasoning about task and project semantics in MySimpleTodos.

## Task Statuses

- `inbox`: captured but not clarified.
- `next_action`: ready to do.
- `waiting_for`: blocked on someone or something else.
- `scheduled`: intended for a later date or has a due date.
- `someday_maybe`: deferred without commitment.
- `done`: completed and closed.

## Project Semantics

- Projects group related tasks.
- Tasks may exist without a project.
- Project fields: `name`, `description`, `notes` (Markdown), `due_date`, `created_at`, `updated_at`, `archived_at`, `completed_at`.
- Projects can be completed when all their tasks are done (`completed_at` is set).
- Archived projects (`archived_at` set) are excluded from active browsing. Archive exists in the service layer but is not yet exposed via a route.
- The active project list excludes both archived and completed projects.

## Due Date Semantics

- `due_date` is optional.
- The Today view compares against the current local date.
- Overdue and due-today items are distinct UI concepts.

## Recurrence Semantics

- Recurring tasks remain a single persistent task record.
- Completing a recurring task advances the same record's `due_date`.
- `last_completed_at` tracks the previous completion time.
- Non-recurring tasks may use `completed_at` when they are closed.

## Notes Semantics

- Notes are stored as raw Markdown text.
- Render notes as sanitized HTML.
- Plain text is already valid Markdown input.

## API Key Model

- Table: `api_keys`
- Fields: `id`, `name` (user label), `key_hash` (SHA-256 hex digest, unique), `key_suffix` (last 6 chars for display), `created_at`, `last_used_at`.
- Plaintext key format: `mst_<64-hex-chars>` (32 random bytes).
- Only the hash is stored — the plaintext is shown once at creation.
- `last_used_at` is updated on each successful API key authentication.
- Maximum 10 active keys per instance.