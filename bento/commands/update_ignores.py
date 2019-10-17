import sys
from typing import Callable, Set

import click

from bento.context import Context
from bento.util import echo_error, echo_success


def __update_ignores(
    context: Context, tool: str, update_func: Callable[[Set[str]], None]
) -> None:
    config = context.config
    tool_config = config["tools"]
    if tool not in tool_config:
        all_tools = ", ".join(f"'{k}'" for k in tool_config.keys())
        echo_error(f"No tool named '{tool}'. Configured tools are {all_tools}")
        sys.exit(3)

    ignores = set(tool_config[tool].get("ignore", []))
    update_func(ignores)

    tool_config[tool]["ignore"] = list(ignores)

    context.config = config


@click.command()
@click.argument("tool", type=str, nargs=1)
@click.argument("check", type=str, nargs=1)
@click.pass_obj
def disable(context: Context, tool: str, check: str) -> None:
    """
    Disables a check.
    """

    def add(ignores: Set[str]) -> None:
        ignores.add(check)

    __update_ignores(context, tool, add)
    echo_success(f"'{check}' disabled for '{tool}'")


@click.command()
@click.argument("tool", type=str, nargs=1)
@click.argument("check", type=str, nargs=1)
@click.pass_obj
def enable(context: Context, tool: str, check: str) -> None:
    """
    Enables a check.
    """

    def remove(ignores: Set[str]) -> None:
        if check in ignores:
            ignores.remove(check)

    __update_ignores(context, tool, remove)
    echo_success(f"'{check}' enabled for '{tool}'")
