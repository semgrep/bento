from typing import Set

import click

from bento.config import (
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
    Here is a help text
    """


@enable.command()
@click.argument("tool", type=str, nargs=1, autocompletion=get_valid_tools)
@click.pass_obj
def tool(context: Context, tool: str) -> None:
    """
        Enable a tool
    """
    update_tool_run(context, tool, True)
    echo_success(f"{tool} enabled")


@enable.command()
@click.argument("tool", type=str, nargs=1, autocompletion=get_valid_tools)
@click.argument("check", type=str, nargs=1, autocompletion=get_disabled_checks)
@click.pass_obj
def check(context: Context, tool: str, check: str) -> None:
    """
    Enables a check
    """

    def remove(ignores: Set[str]) -> None:
        if check in ignores:
            ignores.remove(check)

    update_ignores(context, tool, remove)
    echo_success(f"'{check}' enabled for '{tool}'")
