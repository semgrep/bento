import itertools
import shutil
import sys
from typing import Collection, List

import click

from bento.formatter.base import FindingsMap, Formatter
from bento.violation import Violation


class Stylish(Formatter):
    """
    Mimics the eslint "stylish" formatter
    """

    SEVERITY_STR = {
        0: click.style("advice ", fg="green"),
        1: click.style("warning", fg="yellow"),
        2: click.style("error  ", fg="red"),
    }

    @staticmethod
    def __print_path(path: str) -> str:
        return path

    def __print_violation(self, violation: Violation, max_message_len: int) -> str:

        line = f"{violation.line:>3d}"
        col = f"{violation.column:<2d}"
        tool_id = f"{violation.tool_id:<14s}"
        rule = f"{violation.check_id:s}"

        message = Formatter.ellipsis_trim(violation.message, max_message_len)

        # save some space for what comes next
        message = f"{message:<{max_message_len}s}"

        if not violation.link:
            link = rule
        else:
            link = self.render_link(rule, violation.link)

        sev_str = Stylish.SEVERITY_STR.get(violation.severity, "unknown")
        sev = f"{sev_str:<7s}"
        return f"{line}:{col} {sev} {message} {tool_id} {link}"

    def dump(self, findings: FindingsMap) -> Collection[str]:
        violations = self.by_path(findings)
        lines = []
        max_message_len = min(max((len(v.message) for v in violations), default=0), 100)

        if sys.stdout.isatty():
            terminal_width, _ = shutil.get_terminal_size((50, 20))
            if terminal_width > 0:
                max_message_len = max(min(max_message_len, terminal_width - 40), 50)

        ordered: List[Violation] = sorted(violations, key=Formatter.path_of)
        for path, vv in itertools.groupby(ordered, Formatter.path_of):
            lines.append(Stylish.__print_path(path))
            for v in sorted(vv, key=lambda v: (v.line, v.column, v.message)):
                lines.append(self.__print_violation(v, max_message_len))
            lines.append("")

        return lines
