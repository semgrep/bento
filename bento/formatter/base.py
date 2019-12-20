from abc import ABC, abstractmethod
from typing import Any, Collection, Dict, List, Mapping, Optional

from bento.violation import Violation

FindingsMap = Mapping[str, Collection[Violation]]


class Formatter(ABC):
    """
    Converts tool violations into printable output
    """

    BOLD = "\033[1m"
    END = "\033[0m"

    def __init__(self) -> None:
        self._config: Optional[Dict[str, Any]] = None

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
