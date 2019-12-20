import itertools
import shutil
import sys
from typing import Collection, List

import click

from bento.formatter.base import FindingsMap, Formatter
from bento.util import Colors, render_link
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
        return f"     {arrow} {path}:{line}:{col}"

    def __print_violation(self, violation: Violation, max_message_len: int) -> str:
        message = Clippy.ellipsis_trim(violation.message, max_message_len)

        # save some space for what comes next
        message = f"{message:<{max_message_len}s}"

        nl = "\n"
        pipe = click.style("|", fg="blue")
        violation_message = f"      = {Clippy.BOLD}note:{Clippy.END} {message}{nl}"

        # Strip so trailing newlines are not printed out
        context = violation.syntactic_context.rstrip()

        if context:
            formatted_context = ""
            for offset, line in enumerate(context.split("\n")):
                line = line.rstrip()
                line_no = click.style(
                    f"{violation.line + offset:>4d}", fg=Colors.STATUS
                )
                formatted_context += f" {line_no} {pipe}   {line}{nl}"

            violation_message = (
                f"      {pipe}{nl}" f"{formatted_context}" f"      {pipe}{nl}"
            ) + violation_message
        return violation_message

    def __print_error_message(self, violation: Violation) -> str:
        tool_id = f"{violation.tool_id}".strip()
        rule = f"{violation.check_id}".strip()

        full_rule = f"{tool_id}.{rule}"

        if not violation.link:
            link = full_rule
        else:
            link = render_link(full_rule, violation.link)

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

                violation_message = self.__print_violation(v, max_message_len)
                for l in violation_message.split("\n"):
                    lines.append(l)
            lines.append("")

        return lines
