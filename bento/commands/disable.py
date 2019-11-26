from typing import Set

import click

from bento.config import get_valid_tools, update_ignores, update_tool_run
from bento.context import Context
from bento.util import echo_success


@click.group()
def disable() -> None:
    """
    Disable a tool or check
    """


@disable.command()
@click.argument("tool", type=str, nargs=1, autocompletion=get_valid_tools)
@click.pass_obj
def tool(context: Context, tool: str) -> None:
    """
    Disable a tool
    """
    update_tool_run(context, tool, False)
    echo_success(f"{tool} disabled")


@disable.command()
@click.argument("tool", type=str, nargs=1, autocompletion=get_valid_tools)
@click.argument("check", type=str, nargs=1)
@click.pass_obj
def check(context: Context, tool: str, check: str) -> None:
    """
    Disables a check
    """

    def add(ignores: Set[str]) -> None:
        ignores.add(check)

    update_ignores(context, tool, add)
    echo_success(f"'{check}' disabled for '{tool}'")
