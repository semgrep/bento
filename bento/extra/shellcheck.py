import json
import os
import re
import subprocess
from typing import Any, Dict, Iterable, List, Pattern, Set, Type

from bento.base_context import BaseContext
from bento.parser import Parser
from bento.tool import StrTool
from bento.util import echo_success, fetch_line_in_file
from bento.violation import Violation


class ShellcheckParser(Parser[str]):
    def to_violation(self, result: Dict[str, Any]) -> Violation:
        start_line = result["line"]
        column = result["column"]
        check_id = f"SC{result['code']}"
        message = result["message"]
        path = result["file"]

        path = self.trim_base(path)

        level = result["level"]
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
            tool_id=ShellcheckTool.TOOL_ID,
            check_id=check_id,
            path=path,
            line=start_line,
            column=column,
            message=message,
            severity=severity,
            syntactic_context=line_of_code,
            link=link,
        )

    def parse(self, results: str) -> List[Violation]:
        violations: List[Violation] = []
        for r in json.loads(results):
            violations.append(self.to_violation(r))
        return violations


class ShellcheckTool(StrTool):
    TOOL_ID = "r2c.shellcheck"
    DOCKER_IMAGE = "koalaman/shellcheck:v0.7.0"

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
        return re.compile(r".*\.sh\b")

    def filter_paths(self, paths: Iterable[str]) -> Set[str]:
        """
            Need to find paths to all shell files
        """
        resolved = [os.path.realpath(p) for p in paths]
        valid_paths = {
            e.path
            for e in self.context.file_ignores.entries()
            if e.survives
            if self.file_name_filter.match(os.path.basename(e.path))
            if any(os.path.realpath(e.path).startswith(r) for r in resolved)
        }

        return valid_paths

    @property
    def project_name(self) -> str:
        return "Shell"

    def setup(self) -> None:
        # import inside def for performance
        import docker

        client = docker.from_env()
        if not any(i for i in client.images.list() if self.DOCKER_IMAGE in i.tags):
            client.images.pull(ShellcheckTool.DOCKER_IMAGE)
            echo_success(f"Retrieved {self.TOOL_ID} Container")

    def run(self, files: Iterable[str]) -> str:
        res = self.execute(
            [
                "docker",
                "run",
                "--network",
                "none",
                "--rm",
                "-v",
                f"{os.path.abspath(self.base_path)}:{os.path.abspath(self.base_path)}",
                ShellcheckTool.DOCKER_IMAGE,
                "-f",
                "json",
            ]
            + list(files),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return res.stdout

    @classmethod
    def matches_project(cls, context: BaseContext) -> bool:
        return cls.project_has_extensions(context, "*.sh")
