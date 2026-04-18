---
name: mst-cli
description: Using the MST CLI to manage tasks, projects, and generate reports from the command line.
---
# MST CLI Skill

Use this skill when using the `mst` command-line tool to manage tasks, projects, or generate reports instead of the HTTP API directly.

## Prerequisites

1. CLI installed: `mst --version` should print the version.
2. Config initialized: `~/.mst/config.toml` must exist with server URL and API key.
3. Server running: `mst health` should report healthy.

If the CLI is not installed, run `./scripts/install-cli.sh` from the repo root.

## Quick Start

```bash
# First-time setup (prompts for server URL + API key)
mst config init

# Verify connectivity
mst health
```

## Common Workflows

### Add a task

```bash
mst add "Buy groceries"
mst add "Fix bug in auth" --project 1
```

### Check today's focus

```bash
mst today
```

### Complete a task

```bash
mst complete 42
```

### Change task status

```bash
mst edit 42 --status next_action
```

### Search tasks

```bash
mst tasks --search "groceries"
mst tasks --status inbox
mst tasks --project 1
```

### View a project

```bash
mst projects          # list all projects with task counts
mst project 1         # show project details + tasks grouped by status
```

## Report Generation

The `mst report` command produces a **structured data summary** — not an AI-generated report. It handles data fetching and deterministic task classification.

```bash
mst report               # today's report
mst report --tomorrow    # tomorrow's report
mst report --date 2026-04-01  # specific date
```

### Agent workflow

1. Run `mst report` to get the structured Markdown output.
2. Read the output (Do First, Next Actions, Waiting For, Inbox sections).
3. Layer on LLM-powered recommendations: prioritization, two-minute rule, context batching, project health flags, follow-up nudges.

No API key needs to be stored in agent memory — the CLI reads credentials from `~/.mst/config.toml`.

## Export Data

```bash
mst export tasks                    # JSON to stdout
mst export tasks --format csv       # CSV to stdout
mst export tasks --output out.json  # write to file
mst export tasks --status inbox     # filter by status
mst export projects                 # export projects
mst export projects --format csv    # CSV format
```

## Environment Variable Overrides

| Variable | Purpose |
|---|---|
| `MST_SERVER_URL` | Override server URL (useful for CI / non-standard ports) |
| `MST_API_KEY` | Override API key (useful for CI where config file may not exist) |
| `MST_CONFIG_DIR` | Override config directory (default: `~/.mst`) |

These take precedence over values in `~/.mst/config.toml`.

## Output Formats

- **Rich tables** (default): colored, formatted terminal tables.
- **Plain text** (`--plain` flag): tab-separated output for scripting or piping.
- **JSON/CSV**: via `mst export` commands.

Use `--plain` when parsing output programmatically.

## Error Handling

- `mst health` returns exit code 1 if the server is unreachable.
- All commands show human-readable errors for HTTP failures (404, 500, connection errors).
- If the API key is invalid or missing, the server returns 401 — update with `mst config set auth.api_key <key>`.

## Full Command Reference

| Command | Description |
|---|---|
| `mst config init` | Interactive setup |
| `mst config show` | Show config (masked key) |
| `mst config set KEY VALUE` | Set a config value |
| `mst health` | Check server connectivity |
| `mst inbox` | List inbox tasks |
| `mst today` | Show overdue + due-today tasks |
| `mst tasks [options]` | List/filter/search tasks |
| `mst add TITLE [--project ID]` | Create a task |
| `mst complete ID` | Complete a task |
| `mst reopen ID` | Reopen a task |
| `mst edit ID [options]` | Edit task fields |
| `mst projects` | List projects with counts |
| `mst project ID` | Show project details |
| `mst export tasks [--format --status --output]` | Export tasks |
| `mst export projects [--format --output]` | Export projects |
| `mst report [--date --tomorrow]` | Task data summary |
| `mst --help` | Full help with ASCII banner |
| `mst --version` | Print version |

## Troubleshooting

- **"Cannot connect to server"**: Verify the server is running (`docker compose up`) and the URL in config matches.
- **401 errors**: API key is missing or revoked. Generate a new one from the Settings page and update with `mst config set auth.api_key <key>`.
- **Stale data**: The CLI fetches live data on every invocation. If data seems stale, the server may be running an old database.
