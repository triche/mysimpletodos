"""Health command: gtd health."""

from __future__ import annotations

import click

from gtd_cli.client import GTDClient
from gtd_cli.config import get_api_key, get_server_url


@click.command()
@click.pass_context
def health(ctx: click.Context) -> None:
    """Check server connectivity."""
    server_url = get_server_url(ctx.obj.get("server"))
    api_key = get_api_key()
    try:
        client = GTDClient(server_url, api_key)
        result = client.health()
        if result.get("status") == "ok":
            click.echo(click.style(f"✓ Server is healthy ({server_url})", fg="green"))
        else:
            click.echo(click.style(f"✗ Unexpected response: {result}", fg="red"), err=True)
            ctx.exit(1)
    except click.ClickException as exc:
        click.echo(click.style(f"✗ Server unreachable: {exc.format_message()}", fg="red"), err=True)
        ctx.exit(1)
