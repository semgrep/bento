import logging
import os
import sys
from typing import Any, Callable, List, Set, cast

import click
import yaml

import bento.extra
from bento.context import Context
from bento.extra.click import ClickTool
from bento.extra.grep import GrepTool
from bento.extra.pyre import PyreTool
from bento.extra.sgrep import SGrepTool
from bento.util import AutocompleteSuggestions, echo_error


def update_tool_run(context: Context, tool: str, run: bool) -> None:
    """Sets run field of tool to RUN. Default to no ignore if tool not in config
    """
    # Check that TOOL is valid
    if tool not in {t.tool_id() for t in bento.extra.TOOLS}:
        echo_error(f"No tool named '{tool}'. See help text for list of available tool.")
        sys.exit(3)

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
        exclude = {PyreTool, ClickTool, SGrepTool, GrepTool}
        tool_list = sorted(
            [
                (t.tool_id(), t.tool_desc())
                for t in bento.extra.TOOLS
                if t not in exclude
            ],
            key=(lambda td: td[0]),
        )
        results = list(filter(lambda s: s[0].startswith(incomplete), tool_list))
        return cast(AutocompleteSuggestions, results)
    except Exception as ex:
        logging.warning(ex)
        return []


def get_tool_help(summary: str) -> str:
    tools = get_valid_tools(None, [], "")
    max_width = max(len(t) for t, _ in tools)
    lines = (f"{t:<{max_width}s} -- {d}" for t, d in tools)
    result = "\n    ".join(lines)
    return f"""
  {summary}

  Possible tools are:

    {result}"""


class ToolCommand(click.Command):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.help_summary = kwargs["help_summary"]
        del kwargs["help_summary"]
        super().__init__(*args, **kwargs)

    def format_help_text(self, _: Any, formatter: click.HelpFormatter) -> None:
        formatter.write(get_tool_help(self.help_summary))
        formatter.write("\n")


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
