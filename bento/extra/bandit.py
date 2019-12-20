import json
import re
from typing import Any, Dict, Iterable, List, Pattern, Type

from semantic_version import SimpleSpec

from bento.extra.python_tool import PythonTool
from bento.parser import Parser
from bento.result import Violation
from bento.tool import StrTool
from bento.util import fetch_line_in_file

# Input example:
# {
#   "errors": [
#     {
#       "filename": "./foo.py",
#       "reason": "syntax error while parsing AST from file"
#     }
#   ],
#   "generated_at": "2019-09-17T16:56:51Z",
#   "metrics": {
#     "./bar.py": {
#       "CONFIDENCE.HIGH": 2.0,
#       "CONFIDENCE.LOW": 0.0,
#       "CONFIDENCE.MEDIUM": 0.0,
#       "CONFIDENCE.UNDEFINED": 0.0,
#       "SEVERITY.HIGH": 1.0,
#       "SEVERITY.LOW": 1.0,
#       "SEVERITY.MEDIUM": 0.0,
#       "SEVERITY.UNDEFINED": 0.0,
#       "loc": 3,
#       "nosec": 0
#     },
#     "./foo.py": {
#       "loc": 4,
#       "nosec": 0
#     },
#     "_totals": {
#       "CONFIDENCE.HIGH": 2.0,
#       "CONFIDENCE.LOW": 0.0,
#       "CONFIDENCE.MEDIUM": 0.0,
#       "CONFIDENCE.UNDEFINED": 0.0,
#       "SEVERITY.HIGH": 1.0,
#       "SEVERITY.LOW": 1.0,
#       "SEVERITY.MEDIUM": 0.0,
#       "SEVERITY.UNDEFINED": 0.0,
#       "loc": 7,
#       "nosec": 0
#     }
#   },
#   "results": [
#     {
#       "code": "1 import subprocess\n2 \n3 def do_it(cmd: str) -> None:\n4     subprocess.run(f\"bash -c {cmd}\", shell=True)\n",
#       "filename": "./bar.py",
#       "issue_confidence": "HIGH",
#       "issue_severity": "LOW",
#       "issue_text": "Consider possible security implications associated with subprocess module.",
#       "line_number": 1,
#       "line_range": [
#         1,
#         2
#       ],
#       "more_info": "https://bandit.readthedocs.io/en/latest/blacklists/blacklist_imports.html#b404-import-subprocess",
#       "test_id": "B404",
#       "test_name": "blacklist"
#     },
#     {
#       "code": "3 def do_it(cmd: str) -> None:\n4     subprocess.run(f\"bash -c {cmd}\", shell=True)\n",
#       "filename": "./bar.py",
#       "issue_confidence": "HIGH",
#       "issue_severity": "HIGH",
#       "issue_text": "subprocess call with shell=True identified, security issue.",
#       "line_number": 4,
#       "line_range": [
#         4
#       ],
#       "more_info": "https://bandit.readthedocs.io/en/latest/plugins/b602_subprocess_popen_with_shell_equals_true.html",
#       "test_id": "B602",
#       "test_name": "subprocess_popen_with_shell_equals_true"
#     }
#   ]
# }


class BanditParser(Parser[str]):
    SEVERITY = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
    LINE_NO_CHARS = "0123456789"

    def __error_to_violation(self, error: Dict[str, Any]) -> Violation:
        return Violation(
            check_id="error",
            tool_id=BanditTool.TOOL_ID,
            path=self.trim_base(error["filename"]),
            severity=2,
            line=0,
            column=0,
            message=error["reason"],
            syntactic_context="",
            link=None,
        )

    def __result_to_violation(self, result: Dict[str, Any]) -> Violation:
        path = self.trim_base(result["filename"])
        link = result.get("more_info", None)

        # Remove bandit line numbers, empty lines, and leading / trailing whitespace
        bandit_source = result["code"].rstrip()  # Remove trailing whitespace

        line_range = result["line_range"]

        def in_line_range(bandit_code_line: str) -> bool:
            # Check if string with format `3 def do_it(cmd: str) -> None:`
            # starts with line number that is within reported line_range
            # of finding
            for idx, ch in enumerate(bandit_code_line):
                if not ch.isdigit():
                    num = int(bandit_code_line[:idx])
                    return num in line_range
            return False

        # bandit might include extra lines before and after
        # a finding. Filter those out and filter out line numbers
        lines = [
            s.lstrip(BanditParser.LINE_NO_CHARS).rstrip()
            for s in bandit_source.split("\n")
            if in_line_range(s)
        ]
        nonempty = [l for l in lines if l]
        source = "\n".join(nonempty)

        if source == "" and result["line_number"] != 0:
            source = (
                fetch_line_in_file(self.base_path / path, result["line_number"])
                or "<no source found>"
            )

        return Violation(
            check_id=result["test_id"],
            tool_id=BanditTool.TOOL_ID,
            path=path,
            line=result["line_number"],
            column=0,
            message=result["issue_text"],
            severity=BanditParser.SEVERITY.get(result["issue_severity"], 1),
            syntactic_context=source,
            link=link,
        )

    def parse(self, tool_output: str) -> List[Violation]:
        results: Dict[str, List[Dict[str, Any]]] = json.loads(tool_output)
        errors = [self.__error_to_violation(e) for e in results.get("errors", [])]
        violations = [self.__result_to_violation(r) for r in results.get("results", [])]
        return errors + violations


class BanditTool(PythonTool[str], StrTool):
    TOOL_ID = "r2c.bandit"  # to-do: versioning?
    VENV_DIR = "bandit"
    PROJECT_NAME = "Python"
    FILE_NAME_FILTER = re.compile(r".*\.py\b")
    PACKAGES = {"bandit": SimpleSpec("~=1.6.2")}

    @property
    def parser_type(self) -> Type[Parser]:
        return BanditParser

    @classmethod
    def tool_id(self) -> str:
        return BanditTool.TOOL_ID

    @classmethod
    def tool_desc(cls) -> str:
        return "Finds common security issues in Python code"

    @classmethod
    def venv_subdir_name(cls) -> str:
        return BanditTool.VENV_DIR

    @property
    def project_name(self) -> str:
        return BanditTool.PROJECT_NAME

    @property
    def file_name_filter(self) -> Pattern:
        return BanditTool.FILE_NAME_FILTER

    def run(self, paths: Iterable[str]) -> str:
        cmd = f"""python "$(which bandit)" --f json -x {self._ignore_param()} -r """
        env, args = PythonTool.sanitize_arguments(paths)
        cmd += " ".join(args)
        return self.venv_exec(cmd, env=env, check_output=False)
