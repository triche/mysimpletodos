"""MST CLI entry point — click group with ASCII art banner."""

from __future__ import annotations

import click

from mst_cli import __version__
from mst_cli.commands.backup import backup_group
from mst_cli.commands.config_cmd import config_group
from mst_cli.commands.export import export_group
from mst_cli.commands.health import health
from mst_cli.commands.projects import project, projects
from mst_cli.commands.report import report
from mst_cli.commands.tasks import add, complete, edit, reopen, tasks
from mst_cli.commands.views import inbox, today
from mst_cli.display import render_colored_banner

BANNER = r"""
  ███╗   ███╗███████╗████████╗
  ████╗ ████║██╔════╝╚══██╔══╝
  ██╔████╔██║███████╗   ██║
  ██║╚██╔╝██║╚════██║   ██║
  ██║ ╚═╝ ██║███████║   ██║
  ╚═╝     ╚═╝╚══════╝   ╚═╝
              MySimpleTodos — CLI
"""


class MSTBanner(click.Group):
    """Click group that shows an ASCII art banner on top-level --help."""

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        if ctx.parent is None:
            formatter.write(render_colored_banner())
        super().format_help(ctx, formatter)


@click.group(cls=MSTBanner)
@click.option("--server", default=None, help="Override server URL for this invocation.")
@click.option("--plain", is_flag=True, default=False, help="Disable rich formatting.")
@click.version_option(version=__version__, prog_name="mst")
@click.pass_context
def cli(ctx: click.Context, server: str | None, plain: bool) -> None:
    """MySimpleTodos command-line interface."""
    ctx.ensure_object(dict)
    ctx.obj["server"] = server
    ctx.obj["plain"] = plain


cli.add_command(config_group, "config")
cli.add_command(health)
cli.add_command(inbox)
cli.add_command(today)
cli.add_command(tasks)
cli.add_command(add)
cli.add_command(complete)
cli.add_command(reopen)
cli.add_command(edit)
cli.add_command(projects)
cli.add_command(project)
cli.add_command(export_group, "export")
cli.add_command(backup_group, "backup")
cli.add_command(report)
