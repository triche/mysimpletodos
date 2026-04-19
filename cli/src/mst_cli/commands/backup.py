"""Backup commands: mst backup download, mst backup restore."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import click

from mst_cli.client import MSTClient
from mst_cli.config import get_api_key, get_server_url


def _make_client(ctx: click.Context) -> MSTClient:
    server_url = get_server_url(ctx.obj.get("server"))
    api_key = get_api_key()
    return MSTClient(server_url, api_key)


@click.group("backup")
def backup_group() -> None:
    """Download or restore the database."""


@backup_group.command("download")
@click.option(
    "--output",
    default=None,
    type=click.Path(),
    help="Destination file path. Defaults to todo-YYYY-MM-DD.db in the current directory.",
)
@click.pass_context
def backup_download(ctx: click.Context, output: str | None) -> None:
    """Download a database backup from the server."""
    client = _make_client(ctx)
    data = client.download_backup()

    if output is None:
        output = f"todo-{date.today().isoformat()}.db"

    dest = Path(output)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)

    size_kb = len(data) / 1024
    click.echo(
        click.style(f"✓ Backup saved to {dest} ({size_kb:.1f} KB)", fg="green")
    )


@backup_group.command("restore")
@click.argument("file", type=click.Path(exists=True))
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@click.pass_context
def backup_restore(ctx: click.Context, file: str, yes: bool) -> None:
    """Restore the server database from a local backup file."""
    src = Path(file)
    data = src.read_bytes()

    if not data.startswith(b"SQLite format 3\x00"):
        raise click.ClickException(f"{file} does not appear to be a valid SQLite database")

    if not yes:
        click.confirm(
            "This will REPLACE all data on the server. Continue?",
            abort=True,
        )

    client = _make_client(ctx)
    client.upload_restore(data, filename=src.name)

    click.echo(click.style("✓ Database restored successfully", fg="green"))
