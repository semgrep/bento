from typing import Set

import click

from bento.commands.autorun import uninstall_autorun
from bento.config import ToolCommand, get_valid_tools, update_ignores, update_tool_run
from bento.context import Context
from bento.decorators import with_metrics
from bento.util import echo_success


@click.group()
def disable() -> None:
    """
        Turn OFF part of Bento's functionality.

        For example, to disable the check `no-unused-var` from `r2c.eslint`:

            $ bento disable check r2c.eslint no-unused-var

        To disable the tool `r2c.bandit`:

            $ bento disable tool r2c.bandit
    """


@disable.command(
    cls=ToolCommand,
    short_help="Specify a tool to enable.",
    help_summary="Turn OFF a tool.",
)
@click.argument("tool", type=str, nargs=1, autocompletion=get_valid_tools)
@with_metrics
@click.pass_obj
def tool(context: Context, tool: str) -> None:
    """
        Turn OFF a tool.

        Tool-specific configurations are saved, and can be reenabled via `bento enable tool [TOOL]`.

        Please see `bento disable --help` for more information.
    """
    update_tool_run(context, tool, False)
    echo_success(f"{tool} disabled")


@disable.command(short_help="Specify a check to disable.")
@click.argument("tool", type=str, nargs=1, autocompletion=get_valid_tools)
@click.argument("check", type=str, nargs=1)
@with_metrics
@click.pass_obj
def check(context: Context, tool: str, check: str) -> None:
    """
        Turn OFF a check.

        Please see `bento disable --help` for more information.
    """

    def add(ignores: Set[str]) -> None:
        ignores.add(check)

    update_ignores(context, tool, add)
    echo_success(f"'{check}' disabled for '{tool}'")


disable.add_command(uninstall_autorun)
