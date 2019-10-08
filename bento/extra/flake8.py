import json
import os
import re
from typing import Any, Dict, Iterable, List, Pattern, Type

from bento.extra.python_tool import PythonTool
from bento.parser import Parser
from bento.result import Violation
from bento.tool import Tool

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


class Flake8Parser(Parser):
    def to_violation(self, result: Dict[str, Any]) -> Violation:
        source = result["physical_line"].rstrip()  # Remove trailing whitespace
        path = result["filename"]

        if not os.path.isabs(path) and path.startswith("./"):
            path = path[2:]
        else:
            path = self.trim_base(path)

        check_id = result["code"]

        if check_id == "E999":
            link = ""
        else:
            link = f"https://lintlyci.github.io/Flake8Rules/rules/{check_id}.html"

        return Violation(
            tool_id=Flake8Tool.TOOL_ID,
            check_id=check_id,
            path=path,
            line=result["line_number"],
            column=result["column_number"],
            message=result["text"],
            severity=2,
            syntactic_context=source,
            link=link,
        )

    def parse(self, input: str) -> List[Violation]:
        results: Dict[str, List[Dict[str, Any]]] = json.loads(input)
        return [self.to_violation(v) for r in results.values() for v in r]


class Flake8Tool(PythonTool, Tool):
    TOOL_ID = "r2c.flake8"  # to-do: versioning?
    VENV_DIR = "flake8"
    PROJECT_NAME = "Python"

    @property
    def parser_type(self) -> Type[Parser]:
        return Flake8Parser

    @property
    def tool_id(self) -> str:
        return Flake8Tool.TOOL_ID

    @property
    def project_name(self) -> str:
        return Flake8Tool.PROJECT_NAME

    @property
    def file_name_filter(self) -> Pattern:
        return re.compile(r".*\.py\b")

    @property
    def venv_subdir(self) -> str:
        return Flake8Tool.VENV_DIR

    def setup(self, config: Dict[str, Any]) -> None:
        self.venv_create()
        if self._packages_installed({"flake8": "3.7.0", "flake8-json": "19.8.0"}):
            return
        cmd = f"{PythonTool.PIP_CMD} install -q flake8 flake8-json"
        result = self.venv_exec(cmd, check_output=True).strip()
        if result:
            print(result)

    def run(self, config: Dict[str, Any], paths: Iterable[str]) -> str:
        cmd = "python $(which flake8) --format=json --exclude=.git,__pycache__,docs/source/conf.py,old,build,dist,.bento "

        env, args = PythonTool.sanitize_arguments(paths)
        cmd += " ".join(args)
        return self.venv_exec(cmd, env=env, check_output=False)
