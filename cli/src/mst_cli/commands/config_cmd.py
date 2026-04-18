"""Config commands: mst config init / show / set."""

from __future__ import annotations

import click

from mst_cli.config import get_api_key, get_server_url, load_config, save_config


@click.group("config")
def config_group() -> None:
    """Manage CLI configuration."""


@config_group.command("init")
@click.option(
    "--url",
    prompt="Server URL",
    default="http://localhost:8080",
    help="MySimpleTodos server URL.",
)
@click.option(
    "--api-key",
    prompt="API key",
    hide_input=True,
    help="API key for authentication.",
)
def config_init(url: str, api_key: str) -> None:
    """Interactive setup: create ~/.mst/config.toml."""
    config = {"server": {"url": url}, "auth": {"api_key": api_key}}
    save_config(config)
    click.echo(click.style("✓ Configuration saved to ~/.mst/config.toml", fg="green"))


@config_group.command("show")
def config_show() -> None:
    """Print current configuration."""
    server_url = get_server_url()
    api_key = get_api_key()
    click.echo(f"Server URL: {server_url}")
    if api_key and len(api_key) > 10:
        masked = api_key[:4] + "••••••" + api_key[-6:]
        click.echo(f"API key:    {masked}")
    elif api_key:
        click.echo(f"API key:    {api_key}")
    else:
        click.echo("API key:    not set")


@config_group.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str) -> None:
    """Set a config value (e.g. server.url, auth.api_key)."""
    config = load_config()
    parts = key.split(".", 1)
    if len(parts) != 2:
        raise click.ClickException(f"Invalid key '{key}'. Use 'server.url' or 'auth.api_key'.")
    section, field = parts
    if section not in ("server", "auth"):
        raise click.ClickException(f"Unknown section '{section}'. Use 'server' or 'auth'.")
    if section not in config:
        config[section] = {}
    config[section][field] = value
    save_config(config)
    click.echo(click.style(f"✓ {key} updated", fg="green"))
