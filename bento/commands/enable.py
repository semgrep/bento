from typing import Set

import click

from bento.commands.autorun import install_autorun
from bento.config import (
    ToolCommand,
    get_disabled_checks,
    get_valid_tools,
    update_ignores,
    update_tool_run,
)
from bento.context import Context
from bento.decorators import with_metrics
from bento.util import echo_success


@click.group()
def enable() -> None:
    """
        Turn ON part of Bento's functionality.

        For example, to enable the check `no-unused-var` from `r2c.eslint`:

            $ bento enable check r2c.eslint no-unused-var

        To enable the tool `r2c.bandit`:

            $ bento enable tool r2c.bandit
    """


@enable.command(
    cls=ToolCommand,
    short_help="Specify a tool to enable.",
    help_summary="Turn ON a tool.",
)
@click.argument("tool", type=str, nargs=1, autocompletion=get_valid_tools)
@with_metrics
@click.pass_obj
def tool(context: Context, tool: str) -> None:
    """
        Turn ON a tool.

        If the tool was previously enabled, the tool's previous
        settings will be used. If no configuration exists, smart defaults will
        be applied.

        See `bento enable --help` for more details.
    """
    update_tool_run(context, tool, True)
    echo_success(f"{tool} enabled")


@enable.command(short_help="Specify a check to enable.")
@click.argument("tool", type=str, nargs=1, autocompletion=get_valid_tools)
@click.argument("check", type=str, nargs=1, autocompletion=get_disabled_checks)
@with_metrics
@click.pass_obj
def check(context: Context, tool: str, check: str) -> None:
    """
        Turn ON a check.

        See `bento enable --help` for more details.
    """

    def remove(ignores: Set[str]) -> None:
        if check in ignores:
            ignores.remove(check)

    update_ignores(context, tool, remove)
    echo_success(f"'{check}' enabled for '{tool}'")


enable.add_command(install_autorun)
