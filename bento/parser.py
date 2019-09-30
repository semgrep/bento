import os
from typing import List

import attr

from bento.result import Violation


@attr.s
class Parser(object):
    base_path = attr.ib(type=str)

    def trim_base(self, path: str) -> str:
        abspath = os.path.abspath(path)
        absbase = os.path.abspath(self.base_path)
        offset = abspath.find(absbase)
        if offset != -1:
            offset = offset + len(absbase) + 1
            return abspath[offset:]
        else:
            return path

    def parse(self, results: str) -> List[Violation]:
        return []
