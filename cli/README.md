# MST CLI

Command-line interface for the [MySimpleTodos](../README.md) application. Communicates with the running server over HTTP using API key authentication.

## Install

### Quick Install (recommended)

```bash
./scripts/install-cli.sh
```

This auto-detects `pipx` or `uv` and installs the `mst` command globally.

### Manual Install

```bash
# Using pipx
pipx install ./cli

# Using uv
uv tool install ./cli

# For development
cd cli && uv sync
```

### Uninstall

```bash
pipx uninstall mst-cli
# or
uv tool uninstall mst-cli
```

## First-Time Setup

```bash
mst config init
```

This prompts for the server URL and API key, then writes `~/.mst/config.toml` with restricted permissions (`0600`).

Generate an API key from the Settings page (gear icon) in the MySimpleTodos web UI.

## Usage

```bash
mst --help               # show ASCII banner + full command list
mst health               # check server connectivity

# Views
mst today            mst today            mst today            mst today            mstamst todaaskmst today            mst today            mst today            mst today            mstamst todaaskmst today            mst today            mst todaBuymst todays"  # create a task
mst add "Fix bugmst adojmst add "Fix bugin a projmst
mmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmmm  # reopenmmmmmmmmmmt edit 42 --status next_action  # change status
mstmstmstmst--mstmstmstmst--mstmst set due date
mst edit 42 --title "New titlemst ediange titmst edProjects
mst projects             # list projects with task cmst projects ject 1          mst prow projectmsetamst projects             # list projects with task cmst projects ject 1          mst prow projectmsetamst projectso smst projects             # list projects with task cmst projects ject 1              mst pro# export prmst projects             # list projects with task cmst projecttamst projects             # list projects with ta summary
mst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst rmst Omst rmst rmst rmst rmst rmst rmst rmst rmst rme API key |
| `MST_CONFIG_DIR` | Override config directory (default: `~/.mst`) |

### Config Commands

```bash
mst config show               mst config show               mst config sho)
msmsmsmsmsmsmsmsmsmsmsmsmsmsmsmsmsmsmsmsmsmsmsmsmsmsmsmsmsmsURL
mst config set auth.api_key mst_newkey      # change API key
```

## Output Formats

- **Rich tables** (default) — colored, formatted tables in the terminal.
- **Plain text** (`--plain`) — tab-separated output for scripting/piping.
- **JSON/CSV** (`mst export`) — full data exports.

## Task Report

The `mst report` command produces a structured Markdown data summary:

- **Do First**: overdue + hard-landscape (due today) tasks.
- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- **N- top.
