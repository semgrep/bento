import json
import re
from typing import Iterable, List, Optional, Pattern, Type

from semantic_version import SimpleSpec

from bento.extra.python_tool import PythonTool
from bento.parser import Parser
from bento.tool import StrTool
from bento.violation import Violation


"""
Input example:

[
    {
        "code": "jinjalint-anchor-missing-noreferrer",
        "column": 8,
        "file_path": "test.html",
        "line": 13,
        "message": "Pages opened with 'target=\"_blank\"' allow the new page to access the original's referrer. This can have privacy implications. Include 'rel=\"noreferrer\"' to prevent this."
    },
    {
        "code": "jinjalint-missing-meta-charset",
        "column": 0,
        "file_path": "test.html",
        "line": 1,
        "message": "HTML missing a meta charset declaration may result in content misinterpretation in certain browsers, and thus XSS. Include a meta charset like '<meta charset=\"UTF-8\">' to avoid misinterpretation."
    },
    {
        "code": "jinjalint-missing-doctype",
        "column": 0,
        "file_path": "test.html",
        "line": 1,
        "message": "HTML missing a DOCTYPE declaration may result in content misinterpretation in certain browsers, and thus XSS. Include a DOCTYPE like '<!DOCTYPE html>' to avoid misinterpretation."
    }
]
"""


class JinjalintParser(Parser[str]):
    SEVERITY = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}

    def parse(self, tool_output: str) -> List[Violation]:
        results = json.loads(tool_output)

        violations = [
            Violation(
                check_id=r["code"],
                tool_id=JinjalintTool.TOOL_ID,
                path=self.trim_base(r["file_path"]),
                severity=JinjalintParser.SEVERITY["MEDIUM"],
                line=r["line"],
                column=r["column"],
                message=r["message"],
                syntactic_context="",
            )
            for r in results
        ]

        return violations


class JinjalintTool(PythonTool[str], StrTool):
    TOOL_ID = "r2c.jinja"
    VENV_DIR = "jinjalint"
    PROJECT_NAME = "Python"
    FILE_NAME_FILTER = re.compile(
        r".*\.(html|jinja|twig)$"
    )  # Jinjalint's default extensions
    PACKAGES = {"r2c-jinjalint": SimpleSpec("==0.6.3")}

    @property
    def shebang_pattern(self) -> Optional[Pattern]:
        return None

    @property
    def parser_type(self) -> Type[Parser]:
        return JinjalintParser

    @classmethod
    def tool_id(self) -> str:
        return JinjalintTool.TOOL_ID

    @classmethod
    def tool_desc(cls) -> str:
        return "Finds common security issues in Jinja templates"

    @classmethod
    def venv_subdir_name(cls) -> str:
        return JinjalintTool.VENV_DIR

    @property
    def project_name(self) -> str:
        return JinjalintTool.PROJECT_NAME

    @property
    def file_name_filter(self) -> Pattern:
        return JinjalintTool.FILE_NAME_FILTER

    def run(self, paths: Iterable[str]) -> str:
        launchpoint: str = str(self.venv_dir() / "bin" / "jinjalint")
        exclude_rules = [
            "--exclude",
            "jinjalint-space-only-indent",
            "--exclude",
            "jinjalint-misaligned-indentation",
        ]
        cmd = ["python", launchpoint, "--json"] + exclude_rules + list(paths)
        return self.venv_exec(cmd, check_output=False)
