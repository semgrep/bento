import itertools
import json
import re
import shutil
import sys
from abc import ABC, abstractmethod
from typing import Any, Collection, Dict, List, Optional

import click

import bento.util
from bento.violation import Violation


class Formatter(ABC):
    """
    Converts tool violations into printable output
    """

    _config: Optional[Dict[str, Any]] = None

    @abstractmethod
    def dump(self, violations: List[Violation]) -> Collection[str]:
        """Formats the list of violations for the end user."""
        pass

    @property
    def config(self) -> Dict[str, Any]:
        """
        Return config for this formatter
        """
        if self._config is None:
            raise AttributeError("config is unset")
        return self._config

    @config.setter
    def config(self, config: Dict[str, Any]) -> None:
        self._config = config


class Stylish(Formatter):
    """
    Mimics the eslint "stylish" formatter
    """

    SEVERITY_STR = {
        0: click.style("advice ", fg="green"),
        1: click.style("warning", fg="yellow"),
        2: click.style("error  ", fg="red"),
    }

    OSC_8 = "\x1b]8;;"
    BEL = "\x07"

    LINK_PRINTER_PATTERN = re.compile("(iterm2|gnome-terminal)", re.IGNORECASE)

    _print_links = bento.util.is_child_process_of(LINK_PRINTER_PATTERN)

    @staticmethod
    def __path_of(violation: Violation) -> str:
        return violation.path

    @staticmethod
    def __print_path(path: str) -> str:
        return path

    @staticmethod
    def ellipsis_trim(str: str, max_length: int) -> str:
        if len(str) > max_length:
            return str[0 : max_length - 3] + "..."
        return str

    def __print_violation(self, violation: Violation, max_message_len: int) -> str:

        line = f"{violation.line:>3d}"
        col = f"{violation.column:<2d}"
        tool_id = f"{violation.tool_id:<14s}"
        rule = f"{violation.check_id:s}"

        message = Stylish.ellipsis_trim(violation.message, max_message_len)

        # save some space for what comes next
        message = f"{message:<{max_message_len}s}"

        if not violation.link:
            link = rule
        else:
            link = self.__link(rule, violation.link)

        sev_str = Stylish.SEVERITY_STR.get(violation.severity, "unknown")
        sev = f"{sev_str:<7s}"
        return f"{line}:{col} {sev} {message} {tool_id} {link}"

    def __link(self, text: str, href: str) -> str:
        """
        Prints a clickable hyperlink output if in a tty; otherwise just prints a text link
        """
        # TODO: Determine if terminal supports links
        if sys.stdout.isatty() and self._print_links:
            return (
                f"{Stylish.OSC_8}{href}{Stylish.BEL}{text}{Stylish.OSC_8}{Stylish.BEL}"
            )
        elif href:
            return f"{text} {href}"
        else:
            return text

    def dump(self, violations: List[Violation]) -> Collection[str]:
        lines = []
        max_message_len = min(max((len(v.message) for v in violations), default=0), 100)

        if sys.stdout.isatty():
            terminal_width, _ = shutil.get_terminal_size((50, 20))
            max_message_len = max(min(max_message_len, terminal_width - 50), 20)

        ordered: List[Violation] = sorted(violations, key=Stylish.__path_of)
        for path, vv in itertools.groupby(ordered, Stylish.__path_of):
            lines.append(Stylish.__print_path(path))
            for v in sorted(vv, key=lambda v: (v.line, v.column)):
                lines.append(self.__print_violation(v, max_message_len))
            lines.append("")

        return lines


class Json(Formatter):
    """Formats output as a single JSON blob."""

    def dump(self, violations: List[Violation]) -> Collection[str]:
        json_obj = [
            {
                "tool_id": violation.tool_id,
                "check_id": violation.check_id,
                "line": violation.line,
                "column": violation.column,
                "message": violation.message,
                "severity": violation.severity,
                "path": violation.path,
            }
            for violation in violations
        ]
        return [json.dumps(json_obj)]


def for_name(name: str, config: Dict[str, Any]) -> Formatter:
    """
    Reflectively instantiates a formatter from a python identifier

    E.g.
      for_name("bento.formatter.Stylish", {})
    returns a new instance of the Stylish formatter

    Parameters:
        name (str): The formatter name, as a python fully qualified identifier
        config (dict): The formatter's configuration (formatter-specific)
    """
    formatter = bento.util.for_name(name)()
    formatter.config = config or {}
    return formatter
