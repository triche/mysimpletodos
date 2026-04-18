"""View commands: mst today, mst inbox."""

from __future__ import annotations

from datetime import date

import click

from mst_cli.client import MSTClient
from mst_cli.config import get_api_key, get_server_url
from mst_cli.display import render_task_table


def _make_client(ctx: click.Context) -> MSTClient:
    server_url = get_server_url(ctx.obj.get("server"))
    api_key = get_api_key()
    return MSTClient(server_url, api_key)


@click.command()
@click.pass_context
def today(ctx: click.Context) -> None:
    """Show overdue and due-today tasks."""
    client = _make_client(ctx)
    all_tasks = client.get_tasks()
    today_date = date.today()
    plain = ctx.obj.get("plain", False)

    # Filter: non-done tasks with a due date <= today
    relevant = []
    for t in all_tasks:
        if t.get("status") == "done":
            continue
        if not t.get("due_date"):
            continue
        try:
            due = date.fromisoformat(t["due_date"])
        except ValueError:
            continue
        if due <= today_date:
            relevant.append((due, t))

    overdue = [t for due, t in relevant if due < today_date]
    due_today = [t for due, t in relevant if due == today_date]

    if overdue:
        click.echo(click.style("── Overdue ──", fg="red", bold=True))
        click.echo(render_task_table(overdue, plain=plain))
    if due_today:
        click.echo(click.style("── Due Today ──", fg="blue", bold=True))
        click.echo(render_task_table(due_today, plain=plain))

    if not overdue and not due_today:
        click.echo(click.style("No overdue or due-today tasks. 🎉", fg="green"))
    else:
        click.echo(click.style(f"{len(overdue)} overdue, {len(due_today)} due today", dim=True))


@click.command()
@click.pass_context
def inbox(ctx: click.Context) -> None:
    """Show inbox tasks."""
    client = _make_client(ctx)
    task_list = client.get_tasks(status="inbox")
    plain = ctx.obj.get("plain", False)
    click.echo(render_task_table(task_list, plain=plain))
    click.echo(click.style(f"{len(task_list)} task(s) in inbox", dim=True))
