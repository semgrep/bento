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


class HadolintParser(Parser[str]):
    def to_violation(self, result: Dict[str, Any]) -> Violation:
        start_line = result["line"]
        column = result["column"]
        check_id = result["code"]
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

        if "DL" in check_id or check_id in ["SC2046", "SC2086"]:
            link = f"https://github.com/hadolint/hadolint/wiki/{check_id}"
        elif "SC" in check_id:
            link = f"https://github.com/koalaman/shellcheck/wiki/{check_id}"
        else:
            link = ""

        line_of_code = (
            fetch_line_in_file(self.base_path / path, start_line) or "<no source found>"
        )

        return Violation(
            tool_id=HadolintTool.TOOL_ID,
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


class HadolintTool(StrTool):
    TOOL_ID = "r2c.hadolint"
    DOCKER_IMAGE = "hadolint/hadolint:v1.17.2-8-g65736cb"

    @property
    def parser_type(self) -> Type[Parser]:
        return HadolintParser

    @classmethod
    def tool_id(cls) -> str:
        return cls.TOOL_ID

    @classmethod
    def tool_desc(cls) -> str:
        return "Finds bugs in Docker files (requires Docker)"

    @property
    def file_name_filter(self) -> Pattern:
        return re.compile("Dockerfile")

    def filter_paths(self, paths: Iterable[str]) -> Set[str]:
        """
            Need to find paths to all Dockerfiles
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
        return "Docker"

    def setup(self) -> None:
        # import inside def for performance
        import docker

        client = docker.from_env()
        if not any(i for i in client.images.list() if self.DOCKER_IMAGE in i.tags):
            client.images.pull(self.DOCKER_IMAGE)
            echo_success(f"Retrieved {self.TOOL_ID} Container")

    def run(self, files: Iterable[str]) -> str:
        outputs: List[Dict[str, Any]] = []
        for file in files:
            # TODO wrap hadolint in r2c analyzer to avoid need for stdin
            res = subprocess.run(
                f"docker run --network none --rm -i {self.DOCKER_IMAGE} hadolint --format json - < {file}",
                shell=True,
                cwd=self.base_path,
                encoding="utf8",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            hadolint_output = res.stdout
            hadolint_json = json.loads(hadolint_output)
            for elem in hadolint_json:
                elem["file"] = file
            outputs += hadolint_json

        return json.dumps(outputs)

    @classmethod
    def matches_project(cls, context: BaseContext) -> bool:
        return cls.project_has_extensions(context, "Dockerfile")
