import os
import re
from typing import Any, Dict, Iterable, List, Pattern, Type

from semantic_version import Version

from bento.base_context import BaseContext
from bento.parser import Parser
from bento.tool import JsonR, JsonTool
from bento.util import fetch_line_in_file
from bento.violation import Violation


class ShellcheckParser(Parser[JsonR]):
    def to_violation(self, result: Dict[str, Any]) -> Violation:

        path = self.trim_base(result["path"])
        start_line = result["start"]["line"]
        start_col = result["start"]["col"]
        message = result.get("extra", {}).get("message")
        check_id = result["check_id"]

        level = result.get("extra", {}).get("level")
        if level == "error":
            severity = 2
        elif level == "warning":
            severity = 1
        elif level == "info":
            severity = 0
        elif level == "style":
            severity = 0

        link = f"https://github.com/koalaman/shellcheck/wiki/{check_id}"
        line_of_code = (
            fetch_line_in_file(self.base_path / path, start_line) or "<no source found>"
        )

        return Violation(
            tool_id=ShellcheckTool.tool_id(),
            check_id=check_id,
            path=path,
            line=start_line,
            column=start_col,
            message=message,
            severity=severity,
            syntactic_context=line_of_code,
            link=link,
        )

    def parse(self, results: JsonR) -> List[Violation]:
        violations: List[Violation] = []
        for check in results:
            violations.append(self.to_violation(check))
        return violations


class ShellcheckTool(JsonTool):
    ANALYZER_NAME = "r2c/shellcheck"
    ANALYZER_VERSION = Version("0.0.1")
    FILE_NAME_FILTER = re.compile(r".*")
    TOOL_ID = "shellcheck"

    @property
    def parser_type(self) -> Type[Parser]:
        return ShellcheckParser

    @classmethod
    def tool_id(cls) -> str:
        return cls.TOOL_ID

    @classmethod
    def tool_desc(cls) -> str:
        return "Finds bugs in shell scripts (requires Docker)"

    @property
    def file_name_filter(self) -> Pattern:
        return self.FILE_NAME_FILTER

    @property
    def project_name(self) -> str:
        return "Shell"

    def setup(self) -> None:
        # import inside def for performance
        from bento.extra.r2c_analyzer import prepull_analyzers

        prepull_analyzers(self.ANALYZER_NAME, self.ANALYZER_VERSION)

    def run(self, files: Iterable[str]) -> JsonR:
        # import inside def for performance
        from bento.extra.r2c_analyzer import run_analyzer_on_local_code

        targets = [os.path.realpath(p) for p in files]

        ignore_files = {
            e.path for e in self.context.file_ignores.entries() if not e.survives
        }
        return run_analyzer_on_local_code(
            self.ANALYZER_NAME,
            self.ANALYZER_VERSION,
            self.base_path,
            ignore_files,
            targets,
        )

    @classmethod
    def matches_project(cls, context: BaseContext) -> bool:
        return cls.project_has_extensions(context, "*.sh")
