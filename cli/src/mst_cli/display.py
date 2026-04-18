"""Display helpers — rich tables and plain-text fallback."""

from __future__ import annotations

import io
from datetime import date

from rich.console import Console
from rich.table import Table

# Task status → rich style mapping
STATUS_STYLES: dict[str, str] = {
    "inbox": "bold yellow",
    "next_action": "bold green",
    "waiting_for": "bold magenta",
    "scheduled": "bold cyan",
    "someday_maybe": "dim",
    "done": "strikethrough dim",
}

# Color gradient for the ASCII banner (one color per line)
_BANNER_COLORS = [
    "bright_cyan",
    "cyan",
    "bright_blue",
    "blue",
    "bright_magenta",
    "magenta",
]

_BANNER_LINES = [
    r"  ███╗   ███╗███████╗████████╗",
    r"  ████╗ ████║██╔════╝╚══██╔══╝",
    r"  ██╔████╔██║███████╗   ██║",
    r"  ██║╚██╔╝██║╚════██║   ██║",
    r"  ██║ ╚═╝ ██║███████║   ██║",
    r"  ╚═╝     ╚═╝╚══════╝   ╚═╝",
]

_BANNER_TAGLINE = "MySimpleTodos — CLI"


def render_colored_banner() -> str:
    """Render the ASCII art banner with a color gradient."""
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=True, width=120, highlight=False)
    console.print()
    for i, line in enumerate(_BANNER_LINES):
        color = _BANNER_COLORS[i % len(_BANNER_COLORS)]
        console.print(f"[{color}]{line}[/{color}]")
    # Centered tagline in bold white
    console.print(f"[bold bright_white]{'':>24}{_BANNER_TAGLINE}[/bold bright_white]")
    console.print()
    return buf.getvalue()


def _today() -> date:
    return date.today()


def _due_style(due_str: str | None, status: str | None) -> str:
    """Return a rich style string based on due date vs today."""
    if not due_str or status == "done":
        return ""
    try:
        due = date.fromisoformat(due_str)
    except ValueError:
        return ""
    today = _today()
    if due < today:
        return "bold red"
    if due == today:
        return "bold blue"
    return ""


def _status_styled(status: str) -> str:
    """Wrap a status string in Rich markup."""
    style = STATUS_STYLES.get(status, "")
    if style:
        return f"[{style}]{status}[/{style}]"
    return status


def render_task_table(tasks: list[dict], plain: bool = False) -> str:
    """Render tasks as a table. Returns string."""
    if plain:
        lines = ["ID\tTitle\tStatus\tDue Date\tProject\tRecurring"]
        for t in tasks:
            proj = t.get("project_name") or t.get("project_id") or ""
            rec = "yes" if t.get("is_recurring") else ""
            lines.append(
                f"{t['id']}\t{t['title']}\t{t.get('status', '')}\t"
                f"{t.get('due_date') or ''}\t{proj}\t{rec}"
            )
        return "\n".join(lines)

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("ID", style="dim", width=5)
    table.add_column("Title", style="bold")
    table.add_column("Status")
    table.add_column("Due Date")
    table.add_column("Project", style="bright_blue")
    table.add_column("⟳", width=3)

    for t in tasks:
        due_str = t.get("due_date") or ""
        style = _due_style(due_str, t.get("status"))
        proj = t.get("project_name") or (str(t["project_id"]) if t.get("project_id") else "")
        rec = "[bright_green]⟳[/bright_green]" if t.get("is_recurring") else ""
        status = t.get("status", "")
        table.add_row(
            str(t["id"]),
            t["title"],
            _status_styled(status),
            f"[{style}]{due_str}[/{style}]" if style else due_str,
            proj,
            rec,
        )

    buf = io.StringIO()
    console = Console(file=buf, force_terminal=True, width=120)
    console.print(table)
    return buf.getvalue()


def render_project_table(
    projects: list[dict], task_counts: dict[int, int] | None = None, plain: bool = False
) -> str:
    """Render projects as a table."""
    if plain:
        lines = ["ID\tName\tDescription\tDue Date\tTasks"]
        for p in projects:
            count = task_counts.get(p["id"], 0) if task_counts else ""
            lines.append(
                f"{p['id']}\t{p['name']}\t{p.get('description') or ''}\t"
                f"{p.get('due_date') or ''}\t{count}"
            )
        return "\n".join(lines)

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("ID", style="dim", width=5)
    table.add_column("Name", style="bold")
    table.add_column("Description")
    table.add_column("Due Date")
    table.add_column("Open Tasks", justify="right", style="bright_green")

    for p in projects:
        count = str(task_counts.get(p["id"], 0)) if task_counts else ""
        table.add_row(
            str(p["id"]),
            p["name"],
            p.get("description") or "",
            p.get("due_date") or "",
            count,
        )

    buf = io.StringIO()
    console = Console(file=buf, force_terminal=True, width=120)
    console.print(table)
    return buf.getvalue()


def render_task_detail(task: dict, plain: bool = False) -> str:
    """Render a single task's full details including notes."""
    if plain:
        lines: list[str] = []
        lines.append(f"Task #{task['id']}: {task['title']}")
        lines.append(f"  Status:    {task.get('status', '')}")
        lines.append(f"  Due Date:  {task.get('due_date') or 'none'}")
        proj = task.get("project_name") or task.get("project_id") or "none"
        lines.append(f"  Project:   {proj}")
        lines.append(f"  Recurring: {'yes' if task.get('is_recurring') else 'no'}")
        if task.get("notes"):
            lines.append(f"  Notes:     {task['notes']}")
        return "\n".join(lines)

    buf = io.StringIO()
    console = Console(file=buf, force_terminal=True, width=120, highlight=False)
    status = task.get("status", "")
    status_style = STATUS_STYLES.get(status, "")
    tid = task['id']
    title = task['title']
    console.print(
        f"[bold bright_white]Task #{tid}:[/bold bright_white] "
        f"[bold]{title}[/bold]"
    )
    if status_style:
        console.print(f"  [dim]Status:[/dim]    [{status_style}]{status}[/{status_style}]")
    else:
        console.print(f"  [dim]Status:[/dim]    {status}")
    due = task.get("due_date") or "none"
    due_style = _due_style(task.get("due_date"), status)
    if due_style:
        console.print(f"  [dim]Due Date:[/dim]  [{due_style}]{due}[/{due_style}]")
    else:
        console.print(f"  [dim]Due Date:[/dim]  {due}")
    proj = task.get("project_name") or task.get("project_id") or "none"
    console.print(f"  [dim]Project:[/dim]   [bright_blue]{proj}[/bright_blue]")
    rec = "[bright_green]yes[/bright_green]" if task.get("is_recurring") else "no"
    console.print(f"  [dim]Recurring:[/dim] {rec}")
    if task.get("notes"):
        console.print(f"  [dim]Notes:[/dim]     {task['notes']}")
    return buf.getvalue()
    return "\n".join(lines)
