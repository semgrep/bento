import json
import logging
import os
import re
import subprocess
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Pattern, Type

from semantic_version import Version

from bento.extra.docker import DOCKER_INSTALLED, get_docker_client
from bento.parser import Parser
from bento.tool import JsonR, JsonTool
from bento.util import fetch_line_in_file
from bento.violation import Violation

if TYPE_CHECKING:
    from docker.models.containers import Container


def convert(obj: Dict[str, Any], target: str) -> Dict[str, Any]:
    """
        Return r2c object
    """
    converted: Dict[str, Any] = {}
    converted["path"] = target
    converted["start"] = {}
    converted["start"]["line"] = obj.get("line")
    converted["start"]["col"] = obj.get("column")
    converted["end"] = {}
    converted["end"]["line"] = obj.get("endLine")
    converted["end"]["col"] = obj.get("endColumn")
    converted["extra"] = {}
    converted["extra"]["message"] = obj.get("message")
    converted["extra"]["level"] = obj.get("level")
    converted["check_id"] = f"SC{obj.get('code')}"
    return converted


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
    ANALYZER_NAME = "koalaman/shellcheck"
    ANALYZER_VERSION = Version("0.7.0")
    FILE_NAME_FILTER = re.compile(r".*\.(sh|bash|ksh|dash)$")
    CONTAINER_NAME = "bento-shell-check-daemon"
    TOOL_ID = "shellcheck"
    SHEBANG_PATTERN = re.compile(r"^#!(.*/|.*env +)(sh|bash|ksh)")

    @property
    def shebang_pattern(self) -> Optional[Pattern]:
        return self.SHEBANG_PATTERN

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

    def ensure_daemon_running(self) -> str:
        client = get_docker_client()

        image_id = (
            f"{self.ANALYZER_NAME}:v{self.ANALYZER_VERSION}"
        )  # note the v in front of the version
        running_containers = client.containers.list(
            filters={"name": self.CONTAINER_NAME, "status": "running"}
        )
        if not running_containers:
            container: "Container" = client.containers.run(  # type: ignore
                image_id,
                command="/dev/fd/0",
                tty=True,
                name=self.CONTAINER_NAME,
                auto_remove=True,
                detach=True,
            )
            logging.info(f"started container with id: {container.id}")
            return container.id
        else:
            return running_containers[0].id

    def setup(self) -> None:
        self.ensure_daemon_running()

    def run(self, files: Iterable[str]) -> JsonR:
        results = []
        targets = {os.path.realpath(p) for p in files}
        container_id = self.ensure_daemon_running()
        for target in targets:
            with open(target, "rb") as stdin_file:
                r = subprocess.run(
                    [
                        "docker",
                        "exec",
                        "-i",
                        container_id,
                        "shellcheck",
                        "--severity",
                        "info",
                        "-f",
                        "json",
                        "/dev/fd/0",
                    ],
                    stdout=subprocess.PIPE,
                    stdin=stdin_file,
                )
                stdin_file.close()
                converted_findings = [
                    convert(finding, target) for finding in json.loads(r.stdout)
                ]
                results.extend(converted_findings)
        return results

    def matches_project(self) -> bool:
        return DOCKER_INSTALLED.value and self.project_has_file_paths()
