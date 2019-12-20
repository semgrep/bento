from typing import Set

import click

from bento.config import (
    ToolCommand,
    get_disabled_checks,
    get_valid_tools,
    update_ignores,
    update_tool_run,
)
from bento.context import Context
from bento.util import echo_success


@click.group()
def enable() -> None:
    """
        Turn ON a tool or check.

        Takes a command specifying the tool or check to be enabled.

        For example, to enable the check `no-unused-var` from `r2c.eslint`:

            $ bento enable check r2c.eslint no-unused-var

        To enable the tool `r2c.bandit`:

            $ bento enable tool r2c.bandit

        These commands modify `.bento.yml` in the current project. If the tool was
        previously enabled and exists in the `.bento.yml`, the tool's previous
        settings will be used. If no configuration exists, smart defaults will
        be applied.
    """


@enable.command(
    cls=ToolCommand,
    short_help="Specify a tool to enable.",
    help_summary="Turn ON a tool.",
)
@click.argument("tool", type=str, nargs=1, autocompletion=get_valid_tools)
@click.pass_obj
def tool(context: Context, tool: str) -> None:
    """
        Turn ON a tool.

        See `bento enable --help` for more detail.
    """
    update_tool_run(context, tool, True)
    echo_success(f"{tool} enabled")


@enable.command(short_help="Specify check")
@click.argument("tool", type=str, nargs=1, autocompletion=get_valid_tools)
@click.argument("check", type=str, nargs=1, autocompletion=get_disabled_checks)
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
