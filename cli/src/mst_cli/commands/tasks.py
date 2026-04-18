"""Task commands: mst tasks, add, complete, reopen, edit."""

from __future__ import annotations

import click

from mst_cli.client import MSTClient
from mst_cli.config import get_api_key, get_server_url
from mst_cli.display import render_task_table


def _make_client(ctx: click.Context) -> MSTClient:
    server_url = get_server_url(ctx.obj.get("server"))
    api_key = get_api_key()
    return MSTClient(server_url, api_key)


@click.command("tasks")
@click.option("--status", default=None, help="Filter by task status.")
@click.option("--search", default=None, help="Search tasks by text (client-side).")
@click.option("--project", default=None, type=int, help="Filter by project ID.")
@click.option("--due", default=None, type=click.Choice(["yes", "no"]), help="Filter by due date.")
@click.option(
    "--recurring",
    default=None,
    type=click.Choice(["yes", "no"]),
    help="Filter by recurring flag.",
)
@click.pass_context
def tasks(
    ctx: click.Context,
    status: str | None,
    search: str | None,
    project: int | None,
    due: str | None,
    recurring: str | None,
) -> None:
    """List and filter tasks."""
    client = _make_client(ctx)
    task_list = client.get_tasks(status=status)

    if search:
        q = search.lower()
        task_list = [
            t
            for t in task_list
            if q in t.get("title", "").lower() or q in (t.get("notes") or "").lower()
        ]

    if project is not None:
        task_list = [t for t in task_list if t.get("project_id") == project]

    if due == "yes":
        task_list = [t for t in task_list if t.get("due_date")]
    elif due == "no":
        task_list = [t for t in task_list if not t.get("due_date")]

    if recurring == "yes":
        task_list = [t for t in task_list if t.get("is_recurring")]
    elif recurring == "no":
        task_list = [t for t in task_list if not t.get("is_recurring")]

    plain = ctx.obj.get("plain", False)
    click.echo(render_task_table(task_list, plain=plain))
    click.echo(click.style(f"{len(task_list)} task(s)", dim=True))


@click.command()
@click.argument("title")
@click.option("--project", default=None, type=int, help="Assign to project ID.")
@click.pass_context
def add(ctx: click.Context, title: str, project: int | None) -> None:
    """Create a new task."""
    client = _make_client(ctx)
    client.create_task(title, project_id=project)
    click.echo(click.style(f'✓ Task created: "{title}"', fg="green"))


@click.command()
@click.argument("task_id", type=int)
@click.pass_context
def complete(ctx: click.Context, task_id: int) -> None:
    """Complete a task."""
    client = _make_client(ctx)
    client.complete_task(task_id)
    click.echo(click.style(f"✓ Task {task_id} completed", fg="green"))


@click.command()
@click.argument("task_id", type=int)
@click.pass_context
def reopen(ctx: click.Context, task_id: int) -> None:
    """Reopen a completed task."""
    client = _make_client(ctx)
    client.reopen_task(task_id)
    click.echo(click.style(f"✓ Task {task_id} reopened", fg="yellow"))


QUICK_UPDATE_FIELDS = {"status", "due_date", "project_id"}


@click.command()
@click.argument("task_id", type=int)
@click.option("--title", default=None, help="New title.")
@click.option("--status", default=None, help="New task status.")
@click.option("--due", default=None, help="Due date (YYYY-MM-DD or empty to clear).")
@click.option("--project", "project_id", default=None, help="Project ID (or empty to clear).")
@click.option("--notes", default=None, help="Notes (Markdown).")
@click.pass_context
def edit(
    ctx: click.Context,
    task_id: int,
    title: str | None,
    status: str | None,
    due: str | None,
    project_id: str | None,
    notes: str | None,
) -> None:
    """Edit task fields."""
    client = _make_client(ctx)

    # Collect provided fields
    fields: dict[str, str] = {}
    if title is not None:
        fields["title"] = title
    if status is not None:
        fields["status"] = status
    if due is not None:
        fields["due_date"] = due
    if project_id is not None:
        fields["project_id"] = project_id
    if notes is not None:
        fields["notes"] = notes

    if not fields:
        raise click.ClickException("No fields specified. Use --title, --status, --due, etc.")

    # Use quick-update for single-field changes on supported fields
    if len(fields) == 1:
        field_name = next(iter(fields))
        if field_name in QUICK_UPDATE_FIELDS:
            client.quick_update_task(task_id, field_name, fields[field_name])
            click.echo(click.style(f"✓ Task {task_id} updated", fg="green"))
            return

    client.update_task(task_id, **fields)
    click.echo(click.style(f"✓ Task {task_id} updated", fg="green"))
