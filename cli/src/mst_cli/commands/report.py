"""Report command: mst report — structured task data summary."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import click

from mst_cli.client import MSTClient
from mst_cli.config import get_api_key, get_server_url


def _make_client(ctx: click.Context) -> MSTClient:
    server_url = get_server_url(ctx.obj.get("server"))
    api_key = get_api_key()
    return MSTClient(server_url, api_key)


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _build_project_map(projects: list[dict]) -> dict[int, str]:
    """Build a mapping from project ID to project name."""
    return {p["id"]: p["name"] for p in projects}


def _build_report(
    tasks: list[dict], projects: list[dict], target_date: date
) -> str:
    """Build the structured task report as Markdown."""
    project_map = _build_project_map(projects)
    lines: list[str] = []

    lines.append(f"## Focus Report — {target_date.isoformat()}")
    lines.append("")

    # Classify tasks
    hard_landscape: list[dict] = []
    overdue: list[dict] = []
    urgent_next: list[dict] = []
    other_next: list[dict] = []
    waiting_for: list[dict] = []
    inbox_tasks: list[dict] = []
    someday_maybe: list[dict] = []
    completed_yesterday: list[dict] = []

    yesterday = target_date - timedelta(days=1)

    for t in tasks:
        status = t.get("status", "")
        due = _parse_date(t.get("due_date"))

        # Count yesterday's completions
        completed_at = t.get("completed_at")
        last_completed = t.get("last_completed_at")
        for ts in [completed_at, last_completed]:
            if ts:
                try:
                    completed_date = datetime.fromisoformat(ts).date()
                    if completed_date == yesterday:
                        completed_yesterday.append(t)
                        break
                except ValueError:
                    pass

        if status == "done":
            continue

        if status == "inbox":
            inbox_tasks.append(t)
            continue

        if status == "someday_maybe":
            someday_maybe.append(t)
            continue

        if status == "waiting_for":
            waiting_for.append(t)
            continue

        if due:
            if due == target_date:
                hard_landscape.append(t)
                continue
            if due < target_date:
                overdue.append(t)
                continue

        if status == "next_action":
            if due and (due - target_date).days <= 3:
                urgent_next.append(t)
            else:
                other_next.append(t)
            continue

        # scheduled or other non-done statuses with future due dates
        # not specifically categorized above

    # Do First section
    do_first = overdue + hard_landscape
    if do_first:
        lines.append("### Do First")
        lines.append("")
        lines.append("| ID | Title | Status | Due Date | Project |")
        lines.append("|---|---|---|---|---|")
        for t in do_first:
            proj = project_map.get(t.get("project_id", -1), "")
            due_str = t.get("due_date") or ""
            status = t.get("status", "")
            lines.append(f"| {t['id']} | {t['title']} | {status} | {due_str} | {proj} |")
        lines.append("")

    # Next Actions
    all_next = urgent_next + other_next
    if all_next:
        lines.append("### Next Actions")
        lines.append("")
        lines.append("| ID | Title | Due Date | Days Remaining | Project |")
        lines.append("|---|---|---|---|---|")
        for t in all_next:
            proj = project_map.get(t.get("project_id", -1), "")
            due = _parse_date(t.get("due_date"))
            due_str = t.get("due_date") or ""
            days_rem = str((due - target_date).days) if due else "—"
            lines.append(f"| {t['id']} | {t['title']} | {due_str} | {days_rem} | {proj} |")
        lines.append("")

    # Waiting For
    if waiting_for:
        lines.append("### Waiting For")
        lines.append("")
        lines.append("| ID | Title | Days Waiting | Project |")
        lines.append("|---|---|---|---|")
        for t in waiting_for:
            proj = project_map.get(t.get("project_id", -1), "")
            created = t.get("created_at")
            days_w = "—"
            if created:
                try:
                    created_date = datetime.fromisoformat(created).date()
                    days_w = str((target_date - created_date).days)
                except ValueError:
                    pass
            lines.append(f"| {t['id']} | {t['title']} | {days_w} | {proj} |")
        lines.append("")

    # Inbox
    if inbox_tasks:
        lines.append(f"### Inbox ({len(inbox_tasks)} tasks to clarify)")
        lines.append("")
        for t in inbox_tasks:
            lines.append(f"- {t['title']}")
        lines.append("")

    # Someday / Maybe
    if someday_maybe:
        lines.append(f"### Someday / Maybe ({len(someday_maybe)})")
        lines.append("")

    # Previous day completions
    lines.append("### Previous Day")
    lines.append("")
    lines.append(
        f"**{len(completed_yesterday)}** task(s) completed on {yesterday.isoformat()}."
    )
    lines.append("")

    return "\n".join(lines)


@click.command()
@click.option("--date", "target_date", default=None, help="Target date (YYYY-MM-DD).")
@click.option("--tomorrow", is_flag=True, default=False, help="Use tomorrow as the target date.")
@click.pass_context
def report(ctx: click.Context, target_date: str | None, tomorrow: bool) -> None:
    """Generate a structured task data summary."""
    client = _make_client(ctx)

    if target_date:
        try:
            td = date.fromisoformat(target_date)
        except ValueError as exc:
            raise click.ClickException(f"Invalid date: {target_date}") from exc
    elif tomorrow:
        td = date.today() + timedelta(days=1)
    else:
        td = date.today()

    tasks = client.get_tasks()
    projects = client.get_projects()
    output = _build_report(tasks, projects, td)
    click.echo(output)
