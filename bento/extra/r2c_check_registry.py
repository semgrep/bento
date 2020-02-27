import json
import logging
import re
from pathlib import PurePath
from typing import Iterable, List, Pattern, Type

from bento.extra.docker import DOCKER_INSTALLED, get_docker_client
from bento.parser import Parser
from bento.tool import JsonR, JsonTool
from bento.util import fetch_line_in_file
from bento.violation import Violation


class SGrepParser(Parser[JsonR]):
    def parse(self, results: JsonR) -> List[Violation]:
        violations: List[Violation] = []
        for check in results:
            check_id = check["check_id"]
            path = self.trim_base(check["path"])
            start_line = check["start"]["line"]
            start_col = check["start"]["col"]
            # Custom way to get check_name for sgrep-lint:0.1.10
            message = check.get("extra", {}).get("message")
            source = (
                fetch_line_in_file(self.base_path / path, start_line)
                or "<no source found>"
            )
            violation = Violation(
                tool_id=SgrepR2cCheckRegistryTool.tool_id(),
                check_id=check_id,
                path=path,
                line=start_line,
                column=start_col,
                message=message,
                severity=2,
                syntactic_context=source,
            )

            violations.append(violation)
        return violations


class SgrepR2cCheckRegistryTool(JsonTool):
    TOOL_ID = "r2c.registry.latest"
    DOCKER_IMAGE = "returntocorp/sgrep:0.4.6"
    FILE_NAME_FILTER = re.compile(r".*")

    @property
    def file_name_filter(self) -> Pattern:
        return self.FILE_NAME_FILTER

    @property
    def project_name(self) -> str:
        return "Python/JS"

    @classmethod
    def tool_id(cls) -> str:
        return cls.TOOL_ID

    @classmethod
    def tool_desc(cls) -> str:
        return "Runs checks from r2c's check registry (experimental; requires Docker)"

    def setup(self) -> None:
        client = get_docker_client()

        if not any(i for i in client.images.list() if self.DOCKER_IMAGE in i.tags):
            client.images.pull(self.DOCKER_IMAGE)
            logging.info(f"Retrieved {self.TOOL_ID} Container")

    def run(self, files: Iterable[str]) -> JsonR:
        targets = [str(PurePath(p).relative_to(self.base_path)) for p in files]

        cmd = [
            "--config=https://r2c.dev/default-r2c-checks",
            "--json",
            "--skip-pattern-validation",
            *targets,
        ]

        client = get_docker_client()

        vols = {str(self.base_path): {"bind": "/home/repo", "mode": "ro"}}
        output_raw = client.containers.run(
            self.DOCKER_IMAGE, auto_remove=True, volumes=vols, command=cmd
        )
        output_str = output_raw.decode("utf-8").strip()
        output = json.loads(output_str)
        return output.get("results", [])

    def matches_project(self) -> bool:
        return DOCKER_INSTALLED.value

    @property
    def parser_type(self) -> Type[Parser]:
        return SGrepParser
