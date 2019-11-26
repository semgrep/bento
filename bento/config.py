import logging
import os
import sys
from typing import Any, Callable, List, Set, cast

import yaml

import bento.extra
from bento.context import Context
from bento.util import AutocompleteSuggestions, echo_error


def update_tool_run(context: Context, tool: str, run: bool) -> None:
    """Sets run field of tool to RUN. Default to no ignore if tool not in config
    """
    config = context.config
    tool_config = config["tools"]
    if tool not in tool_config:
        # Read default ignore from default config file
        with (
            open(os.path.join(os.path.dirname(__file__), "configs/default.yml"))
        ) as template:
            yml = yaml.safe_load(template)

        default_ignore: List[str] = []
        if tool in yml["tools"]:
            default_ignore = yml["tools"][tool]["ignore"]

        tool_config[tool] = {"ignore": default_ignore}

    tool_config[tool]["run"] = run
    context.config = config


def update_ignores(
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


def get_valid_tools(
    ctx: Any, args: List[str], incomplete: str
) -> AutocompleteSuggestions:
    # context is not yet initialized, so just do it now
    try:
        tool_list = [(t.tool_id(), t.tool_desc()) for t in bento.extra.TOOLS]
        results = list(filter(lambda s: s[0].startswith(incomplete), tool_list))
        return cast(AutocompleteSuggestions, results)
    except Exception as ex:
        logging.warning(ex)
        return []


def get_disabled_checks(
    ctx: Any, args: List[str], incomplete: str
) -> AutocompleteSuggestions:
    # context is not yet initialized, so just do it now
    try:
        context = Context()
        results = list(
            filter(
                lambda s: s.startswith(incomplete),
                context.config["tools"][args[-1]]["ignore"],
            )
        )
        return cast(AutocompleteSuggestions, results)
    except Exception:
        return []
