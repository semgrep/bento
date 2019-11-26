import json
import re
from typing import Any, Dict, Iterable, List, Pattern, Type

from semantic_version import SimpleSpec

from bento.extra.python_tool import PythonTool
from bento.parser import Parser
from bento.result import Violation
from bento.tool import StrTool

# Input example:
# {
#     "./foo.py": [
#         {
#             "code": "E124",
#             "filename": "./foo.py",
#             "line_number": 2,
#             "column_number": 9,
#             "text": "closing bracket does not match visual indentation",
#             "physical_line": "        )\n"
#         }
#     ]
# }
#


class Flake8Parser(Parser[str]):
    @staticmethod
    def id_to_link(check_id: str) -> str:
        if check_id == "E999":
            link = ""
        elif check_id in ("E722", "E306", "E117"):
            link = "https://pycodestyle.readthedocs.io/en/latest/intro.html#error-codes"
        else:
            link = f"https://lintlyci.github.io/Flake8Rules/rules/{check_id}.html"
        return link

    @staticmethod
    def id_to_name(check_id: str) -> str:
        return check_id

    @staticmethod
    def tool() -> Type[StrTool]:
        return Flake8Tool

    def to_violation(self, result: Dict[str, Any]) -> Violation:
        source = (result["physical_line"] or "").rstrip()  # Remove trailing whitespace
        path = self.trim_base(result["filename"])

        check_id = result["code"]

        return Violation(
            tool_id=self.tool().tool_id(),
            check_id=self.id_to_name(check_id),
            path=path,
            line=result["line_number"],
            column=result["column_number"],
            message=result["text"],
            severity=2,
            syntactic_context=source,
            link=self.id_to_link(check_id),
        )

    def parse(self, tool_output: str) -> List[Violation]:
        results: Dict[str, List[Dict[str, Any]]] = json.loads(tool_output)
        return [self.to_violation(v) for r in results.values() for v in r]


class Flake8Tool(PythonTool[str], StrTool):
    TOOL_ID = "r2c.flake8"  # to-do: versioning?
    VENV_DIR = "flake8"
    PROJECT_NAME = "Python"
    PACKAGES = {
        "flake8": SimpleSpec("~=3.7.0"),
        "flake8-json": SimpleSpec("~=19.8.0"),
        "flake8-bugbear": SimpleSpec("~=19.8.0"),
        "flake8-builtins": SimpleSpec("~=1.4.1"),
        "flake8-debugger": SimpleSpec("~=3.2.0"),
        "flake8-executable": SimpleSpec("~=2.0.3"),
    }

    @property
    def parser_type(self) -> Type[Parser]:
        return Flake8Parser

    @classmethod
    def tool_id(cls) -> str:
        return cls.TOOL_ID

    @classmethod
    def tool_desc(cls) -> str:
        return "Finds common bugs in Python code"

    @property
    def project_name(self) -> str:
        return self.PROJECT_NAME

    @property
    def file_name_filter(self) -> Pattern:
        return re.compile(r".*\.py\b")

    @classmethod
    def venv_subdir_name(self) -> str:
        return self.VENV_DIR

    def select_clause(self) -> str:
        """Returns a --select argument to identify which checks flake8 should run"""
        return ""

    def run(self, paths: Iterable[str]) -> str:
        cmd = f"""python "$(which flake8)" {self.select_clause()} --format=json --exclude={self._ignore_param().replace(" ", "*")} """  # stupid hack to deal with spaces in flake8 exclude see https://stackoverflow.com/a/53176372
        env, args = PythonTool.sanitize_arguments(paths)
        cmd += " ".join(args)
        return self.venv_exec(cmd, env=env, check_output=False)
