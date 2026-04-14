"""Project commands: gtd projects, gtd project ID."""

from __future__ import annotations

import click

from gtd_cli.client import GTDClient
from gtd_cli.config import get_api_key, get_server_url
from gtd_cli.display import render_project_table, render_task_table

STATUS_ORDER = ["inbox", "next_action", "waiting_for", "scheduled", "someday_maybe", "done"]
STATUS_LABELS = {
    "inbox": "Inbox",
    "next_action": "Next Action",
    "waiting_for": "Waiting For",
    "scheduled": "Scheduled",
    "someday_maybe": "Someday / Maybe",
    "done": "Done",
}


def _make_client(ctx: click.Context) -> GTDClient:
    server_url = get_server_url(ctx.obj.get("server"))
    api_key = get_api_key()
    return GTDClient(server_url, api_key)


@click.command("projects")
@click.pass_context
def projects(ctx: click.Context) -> None:
    """List all projects with open task counts."""
    client = _make_client(ctx)
    project_list = client.get_projects()
    all_tasks = client.get_tasks()
    plain = ctx.obj.get("plain", False)

    # Compute open task counts per project
    task_counts: dict[int, int] = {}
    for t in all_tasks:
        pid = t.get("project_id")
        if pid and t.get("status") != "done":
            task_counts[pid] = task_counts.get(pid, 0) + 1

    # Filter to non-completed, non-archived projects
    active = [
        p
        for p in project_list
        if not p.get("completed_at") and not p.get("archived_at")
    ]

    click.echo(render_project_table(active, task_counts=task_counts, plain=plain))
    click.echo(click.style(f"{len(active)} project(s)", dim=True))


@click.command("project")
@click.argument("project_id", type=int)
@click.pass_context
def project(ctx: click.Context, project_id: int) -> None:
    """Show a project with its tasks grouped by status."""
    client = _make_client(ctx)
    project_list = client.get_projects()
    plain = ctx.obj.get("plain", False)

    proj = None
    for p in project_list:
        if p["id"] == project_id:
            proj = p
            break

    if not proj:
        raise click.ClickException(f"Project {project_id} not found.")

    click.echo(click.style(f"Project: {proj['name']}", fg="bright_blue", bold=True))
    if proj.get("description"):
        click.echo(f"  {proj['description']}")
    if proj.get("notes"):
        click.echo(click.style(f"  Notes: {proj['notes']}", dim=True))
    if proj.get("due_date"):
        click.echo(f"  Due: {proj['due_date']}")
    click.echo()

    all_tasks = client.get_tasks()
    project_tasks = [t for t in all_tasks if t.get("project_id") == project_id]

    for status_key in STATUS_ORDER:
        group = [t for t in project_tasks if t.get("status") == status_key]
        if group:
            label = STATUS_LABELS.get(status_key, status_key)
            click.echo(click.style(f"── {label} ──", fg="cyan", bold=True))
            click.echo(render_task_table(group, plain=plain))
