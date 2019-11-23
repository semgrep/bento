import itertools
import shutil
import sys
from typing import Collection, List

import click

from bento.formatter.base import FindingsMap, Formatter
from bento.util import Colors
from bento.violation import Violation


class Clippy(Formatter):
    """
    Mimics the eslint "clippy" formatter
    """

    SEVERITY_STR = {
        0: click.style("advice", fg=Colors.SUCCESS),
        1: click.style("warning", fg=Colors.WARNING),
        2: click.style("error", fg=Colors.ERROR),
    }

    @staticmethod
    def __print_path(path: str, line: int, col: int) -> str:
        arrow = click.style("-->", fg="blue")
        return f"   {arrow} {path}:{line}:{col}"

    def __print_violation(self, violation: Violation, max_message_len: int) -> str:
        line = click.style(f"{violation.line:>4d}", fg=Colors.STATUS)

        message = Clippy.ellipsis_trim(violation.message, max_message_len)

        # save some space for what comes next
        message = f"{message:<{max_message_len}s}"

        nl = "\n"

        context = violation.syntactic_context.rstrip("\n\r").strip()
        context = context.replace("\n", "")

        violation_message = f"    = {Clippy.BOLD}note:{Clippy.END} {message}{nl}"
        pipe = click.style("|", fg="blue")

        if context:
            violation_message = (
                f"      {pipe}{nl}"
                f" {line} {pipe}   {context}{nl}"
                f"      {pipe}{nl}"
            ) + violation_message
        return violation_message

    def __print_error_message(self, violation: Violation) -> str:
        tool_id = f"{violation.tool_id}".strip()
        rule = f"{violation.check_id}".strip()

        full_rule = f"{tool_id}.{rule}"

        if not violation.link:
            link = full_rule
        else:
            link = self.render_link(full_rule, violation.link)

        sev_str = Clippy.SEVERITY_STR.get(violation.severity, "unknown")
        sev = f"{sev_str}".strip()

        return f"{Clippy.BOLD}{sev}: {Clippy.BOLD}{link}{Clippy.END}"

    def __print_summary(self) -> str:
        return f"{Clippy.BOLD}==> Bento Summary{Clippy.END}"

    def dump(self, findings: FindingsMap) -> Collection[str]:
        violations = self.by_path(findings)
        lines = [self.__print_summary()]
        max_message_len = min(max((len(v.message) for v in violations), default=0), 200)

        if sys.stdout.isatty():
            terminal_width, _ = shutil.get_terminal_size((50, 20))
            max_message_len = max(min(max_message_len, terminal_width - 10), 20)

        ordered: List[Violation] = sorted(violations, key=Formatter.path_of)

        for path, vv in itertools.groupby(ordered, Formatter.path_of):
            for v in sorted(vv, key=lambda v: (v.line, v.column, v.message)):
                lines.append(self.__print_error_message(v))
                lines.append(Clippy.__print_path(path, v.line, v.column))
                lines.append(self.__print_violation(v, max_message_len))
            lines.append("")

        return lines
