import re
from pathlib import Path
from typing import Iterable, List, Pattern, Type

from semantic_version import Version

from bento.extra.r2c_analyzer import prepull_analyzers, run_analyzer_on_local_code
from bento.parser import Parser
from bento.tool import JsonR, output
from bento.violation import Violation


class CheckedReturnParser(Parser[JsonR]):
    def parse(self, results: JsonR) -> List[Violation]:
        violations: List[Violation] = []
        for check in results:
            path = self.trim_base(check["path"])
            start_line = check["start"]["line"]
            start_col = check["start"]["col"]
            check_id = check["check_id"]

            violation = Violation(
                tool_id=CheckedReturnTool.tool_id(),
                check_id=check_id,
                path=path,
                line=start_line,
                column=start_col,
                message=check.get("extra", {}).get("message"),
                severity=2,
                syntactic_context=check.get("extra", {}).get("line"),
            )

            violations.append(violation)
        return violations


class CheckedReturnTool(output.Json):
    ANALYZER_NAME = "r2c/checked-return"
    ANALYZER_VERSION = Version("0.1.11")
    FILE_NAME_FILTER = re.compile(r".*")

    @property
    def file_name_filter(self) -> Pattern:
        return self.FILE_NAME_FILTER

    @property
    def project_name(self) -> str:
        return "Python/JS"

    @classmethod
    def tool_id(cls) -> str:
        return "r2c.checked_return"

    @classmethod
    def tool_desc(cls) -> str:
        return "Finds anomalous use of return values (experimental)"

    def setup(self) -> None:
        prepull_analyzers(self.ANALYZER_NAME, self.ANALYZER_VERSION)

    def run(self, files: Iterable[str]) -> JsonR:
        return run_analyzer_on_local_code(
            self.ANALYZER_NAME, self.ANALYZER_VERSION, self.base_path, files
        )

    def matches_project(self, files: Iterable[Path]) -> bool:
        return True

    @property
    def parser_type(self) -> Type[Parser]:
        return CheckedReturnParser
