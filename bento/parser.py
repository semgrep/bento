import os
from pathlib import Path
from typing import List

import attr

from bento.result import Violation


def _absolute(path: Path) -> Path:
    return path.absolute()


@attr.s
class Parser(object):
    base_path = attr.ib(type=Path, converter=_absolute)

    def trim_base(self, path: str) -> str:
        wrapped = Path(path)
        if not wrapped.is_absolute():
            wrapped = self.base_path / wrapped
        return os.path.relpath(wrapped, self.base_path)

    def parse(self, results: str) -> List[Violation]:
        return []
