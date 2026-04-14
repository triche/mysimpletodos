"""Export commands: gtd export tasks, gtd export projects."""

from __future__ import annotations

from pathlib import Path

import click

from gtd_cli.client import GTDClient
from gtd_cli.config import get_api_key, get_server_url


def _make_client(ctx: click.Context) -> GTDClient:
    server_url = get_server_url(ctx.obj.get("server"))
    api_key = get_api_key()
    return GTDClient(server_url, api_key)


@click.group("export")
def export_group() -> None:
    """Export tasks or projects."""


@export_group.command("tasks")
@click.option(
    "--format",
    "fmt",
    default="json",
    type=click.Choice(["json", "csv"]),
    help="Output format.",
)
@click.option("--status", default=None, help="Filter by GTD status.")
@click.option("--output", default=None, type=click.Path(), help="Write to file instead of stdout.")
@click.pass_context
def export_tasks(ctx: click.Context, fmt: str, status: str | None, output: str | None) -> None:
    """Export tasks as JSON or CSV."""
    client = _make_client(ctx)
    data = client.export_tasks(fmt=fmt, status=status)
    if output:
        Path(output).write_text(data)
        click.echo(click.style(f"✓ Tasks exported to {output}", fg="green"))
    else:
        click.echo(data)


@export_group.command("projects")
@click.option(
    "--format",
    "fmt",
    default="json",
    type=click.Choice(["json", "csv"]),
    help="Output format.",
)
@click.option("--output", default=None, type=click.Path(), help="Write to file instead of stdout.")
@click.pass_context
def export_projects(ctx: click.Context, fmt: str, output: str | None) -> None:
    """Export projects as JSON or CSV."""
    client = _make_client(ctx)
    data = client.export_projects(fmt=fmt)
    if output:
        Path(output).write_text(data)
        click.echo(click.style(f"✓ Projects exported to {output}", fg="green"))
    else:
        click.echo(data)
