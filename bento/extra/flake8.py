import json
import os
import re
import subprocess
import venv
from typing import Any, Dict, Iterable, List, Pattern, Type

import bento.constants
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
        source = result["physical_line"][:-1]  # Remove trailing newline
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
            tool_id=Flake8Tool.FLAKE8_TOOL_ID,
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


class Flake8Tool(Tool):
    FLAKE8_TOOL_ID = "r2c.flake8"  # to-do: versioning?
    VENV_DIR = "flake8"
    PROJECT_NAME = "Python"

    _venv_dir = ""

    @property
    def parser_type(self) -> Type[Parser]:
        return Flake8Parser

    @property
    def tool_id(self) -> str:
        return Flake8Tool.FLAKE8_TOOL_ID

    @property
    def project_name(self) -> str:
        return Flake8Tool.PROJECT_NAME

    @property
    def file_name_filter(self) -> Pattern:
        return re.compile(r".*\.py\b")

    def __venv_dir(self) -> str:
        return os.path.join(
            self.base_path, bento.constants.RESOURCE_DIR, Flake8Tool.VENV_DIR
        )

    def __venv_exec(self, cmd: str, check_output: bool = True) -> str:
        wrapped = f"source {self.__venv_dir()}/bin/activate; {cmd}"
        v = subprocess.Popen(
            wrapped,
            shell=True,
            cwd=self.base_path,
            encoding="utf8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = v.communicate()
        if check_output and v.returncode != 0:
            raise subprocess.CalledProcessError(
                v.returncode, wrapped, output=stdout, stderr=stderr
            )
        return stdout

    def setup(self, config: Dict[str, Any]) -> None:
        venv.create(self.__venv_dir(), with_pip=True, symlinks=True)
        cmd = "pip3 install -q flake8 flake8-json"
        result = self.__venv_exec(cmd, check_output=True).strip()
        if result:
            print(result)

    def run(self, config: Dict[str, Any], files: Iterable[str]) -> str:
        cmd = "flake8 --format=json --exclude=.git,__pycache__,docs/source/conf.py,old,build,dist,.bento "
        cmd += " ".join(files)
        return self.__venv_exec(cmd, check_output=False)
