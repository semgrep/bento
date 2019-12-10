import json
import re
from typing import Iterable, List, Pattern, Type

from semantic_version import Version

from bento.base_context import BaseContext
from bento.extra.r2c_analyzer import prepull_analyzers, run_analyzer_on_local_code
from bento.parser import Parser
from bento.tool import StrTool
from bento.util import fetch_line_in_file
from bento.violation import Violation


class PythonTaintParser(Parser[str]):
    def parse(self, results: str) -> List[Violation]:
        violations: List[Violation] = []
        checks = json.loads(results).get("results", [])
        for check in checks:
            path = self.trim_base(check["path"])
            start_line = check["start"]["line"]
            start_col = check["start"]["col"]
            check_id = check["check_id"]

            line_of_code = (
                fetch_line_in_file(self.base_path / path, start_line)
                or "<no source found>"
            )

            violation = Violation(
                tool_id=PythonTaintTool.tool_id(),
                check_id=check_id,
                path=path,
                line=start_line,
                column=start_col,
                message=check.get("extra", {}).get("description"),
                severity=2,
                syntactic_context=line_of_code,
            )

            violations.append(violation)
        return violations


class PythonTaintTool(StrTool):
    ANALYZER_NAME = "r2c/pyre-taint"
    ANALYZER_VERSION = Version("0.0.9")
    FILENAME_PATTERN = re.compile(".*py")

    @property
    def file_name_filter(self) -> Pattern:
        return re.compile(PythonTaintTool.FILENAME_PATTERN)

    @property
    def project_name(self) -> str:
        return "Python"

    @classmethod
    def tool_desc(cls) -> str:
        return "Runs a Python taint analysis"

    @classmethod
    def tool_id(cls) -> str:
        return "PythonTaint"

    def setup(self) -> None:
        prepull_analyzers(self.ANALYZER_NAME, self.ANALYZER_VERSION)

    def run(self, files: Iterable[str]) -> str:
        ignore_files = {
            e.path for e in self.context.file_ignores.entries() if not e.survives
        }
        return run_analyzer_on_local_code(
            self.ANALYZER_NAME, self.ANALYZER_VERSION, self.base_path, ignore_files
        )

    @classmethod
    def matches_project(cls, context: BaseContext) -> bool:
        return True

    @property
    def parser_type(self) -> Type[Parser]:
        return PythonTaintParser
