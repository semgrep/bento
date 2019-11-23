import re
import sys
from abc import ABC, abstractmethod
from typing import Any, Collection, Dict, List, Mapping, Optional

import bento.util
from bento.violation import Violation

FindingsMap = Mapping[str, Collection[Violation]]

LINK_PRINTER_PATTERN = re.compile("(iterm2|gnome-terminal)", re.IGNORECASE)


class Formatter(ABC):
    """
    Converts tool violations into printable output
    """

    OSC_8 = "\x1b]8;;"
    BEL = "\x07"
    LINK_WIDTH = 2 * len(OSC_8) + 2 * len(BEL)

    BOLD = "\033[1m"
    END = "\033[0m"

    def __init__(self) -> None:
        self._config: Optional[Dict[str, Any]] = None
        self._print_links = bento.util.is_child_process_of(LINK_PRINTER_PATTERN)

    @abstractmethod
    def dump(self, findings: FindingsMap) -> Collection[str]:
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

    @staticmethod
    def path_of(violation: Violation) -> str:
        return violation.path

    @staticmethod
    def by_path(findings: FindingsMap) -> List[Violation]:
        collapsed = (v for violations in findings.values() for v in violations)
        return sorted(collapsed, key=(lambda v: v.path))

    @staticmethod
    def ellipsis_trim(untrimmed: str, max_length: int) -> str:
        if len(untrimmed) > max_length:
            return untrimmed[0 : max_length - 3] + "..."
        return untrimmed

    def render_link(
        self,
        text: str,
        href: Optional[str],
        print_alternative: bool = True,
        width: Optional[int] = None,
    ) -> str:
        """
        Prints a clickable hyperlink output if in a tty; otherwise just prints a text link

        :param text: The link anchor text
        :param href: The href, if exists
        :param print_alternative: If true, only emits link if OSC8 links are supported, otherwise prints href after text
        :param width: Minimum link width
        :return: The rendered link
        """
        if href is not None and sys.stdout.isatty() and self._print_links:
            text = f"{Formatter.OSC_8}{href}{Formatter.BEL}{text}{Formatter.OSC_8}{Formatter.BEL}"
            if width:
                width += Formatter.LINK_WIDTH + len(href)
        elif href and print_alternative:
            text = f"{text} {href}"

        if width:
            return text.ljust(width)
        else:
            return text
