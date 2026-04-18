---
name: daily-report
description: Generate a daily focus report, tomorrow's priorities, or a task review from live task data.
---
# Daily Focus Report Skill

Use this skill when the user asks for a daily report, focus plan, tomorrow's priorities, or a task review.

## How to Generate the Report

> **Important:** Always use the `mst` CLI to fetch data. Do NOT query the SQLite database directly via `docker exec`, and do NOT use `curl` against the HTTP API. The CLI handles authentication and connectivity automatically via `~/.mst/config.toml`.

### Step 1: Verify connectivity

```bash
mst health
```

If the CLI is not installed, run `./scripts/install-cli.sh` from the repo root. If the server is unreachable, tell the user to start it with `docker compose up -d --build`.

### Step 2: Fetch the structured report

```bash
mst report               # today's report
mst report --tomorrow    # tomorrow's report
mst report --damst report --damst report --damst report --damst report --damst report --damst report --da with Do First, Next Actimst report --damst report --damst report --damst report --damst report --damst report --damst report pplemsntmst report --damst repobash
mst report --damst report --damst report --damst report --damst report --damst report --damst reportect health (open task counts)
```

### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ###  th### ### ### ### ### ### ###from the open tasks (status != `done`):

1. **Hard Landscape** — tasks with `due_date` equal to the target date. These are non-negotiable commitments.
2. **Overdue** — tasks with `due_date` before the target date. These need immediate attention.
3. **Urgent Next Actions** — tasks with sta3. **Urgent Next Actions** — tasks with sta3. **Urgent Next Actions** — tasks with sta3. **Urgent Next Actions** — tasks with sta3. **Urgent Next Actions** — tasks with sta3. **Urgent Next Actions** — tasks with sta3. **Urgent Next Actions** — tasks with sta3. **Urgent Next Actions** — tasks `some3. **Urgent Next Actions** — tasks with sta3. **Urgent Next Actions** — tasks with sta3. **Urgent Next Actions** — tasks whe3.epo3. **Urgent Next Actions** — tasks with sta3. **Urgent Next Actions** — tasks with sta3. **Urgent Next Actions** — tasks with sta3. **Urgent Next Actions** — tasks with sta3. **Urgent Next Actions** — tasks with sta3. **Urgent Next Actions** — tasks with sta3. **Urgent Next Actions** — tasks with sta3. **3-5 actionable bullet points advising how to spend the day. Reference specific tasks and projects. Consider time-sensitivity, dependencies, and quick wins.
- **Previous Day's Wins**: Count of tasks completed on the current date (tasks where `completed_at` matches today). Provides momentum context.

### Step 7: Resolve project names

The CLI output already includes project names. If any are missing, use `mst project <id>` to look them up.

## Report Format

Use Markdown with:
- H2 for the report title (include the target date)
- H3 for each section
- Tables for task lists
- Blockquotes for the #1 priority callout
- Bold for due dates that are within 2 days

## Task Management Principles to Apply

- **Two-minute rule**: If a task can be done in < 2 minutes, recommend doing it first.
- **Context batching**: Group similar tasks when recommending order of work.
- **Weekly Review prep**: If it's Friday, remind user to do a weekly review.
- **Project health**: Flag any active project that has zero next actions.
