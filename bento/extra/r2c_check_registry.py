import json
import logging
import os
import re
import uuid
from pathlib import PurePath
from typing import TYPE_CHECKING, Iterable, List, Pattern, Type

from bento.extra.docker import DOCKER_INSTALLED, copy_into_container, get_docker_client
from bento.parser import Parser
from bento.tool import JsonR, JsonTool
from bento.util import fetch_line_in_file
from bento.violation import Violation

if TYPE_CHECKING:
    from docker.models.containers import Container


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
    CONTAINER_NAME = f"bento-sgrep-daemon-{str(uuid.uuid4())[:8]}"
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

    @property
    def use_remote_docker(self) -> bool:
        """Return whether the Docker daemon is remote.
        
        We need to know because volume mounting doesn't work with remote daemons.
        """
        return os.getenv("R2C_USE_REMOTE_DOCKER", "0") == "1"

    def setup(self) -> None:
        self.prepull_image()
        if self.use_remote_docker:
            self.get_or_start_daemon()

    def prepull_image(self) -> None:
        client = get_docker_client()

        if not any(i for i in client.images.list() if self.DOCKER_IMAGE in i.tags):
            client.images.pull(self.DOCKER_IMAGE)
            logging.info(f"Pre-pulled {self.TOOL_ID} image")

    def get_or_start_daemon(self) -> "Container":
        client = get_docker_client()

        our_containers = client.containers.list(
            filters={"name": self.CONTAINER_NAME, "status": "running"}
        )
        if our_containers:
            logging.info(f"using existing {self.TOOL_ID} container")
            return our_containers[0]

        logging.info(f"starting new {self.TOOL_ID} container")
        container: "Container" = client.containers.run(  # type: ignore
            self.DOCKER_IMAGE,
            entrypoint=["sleep"],
            command=[f"{24 * 60 * 60}"],
            auto_remove=True,
            name=self.CONTAINER_NAME,
            detach=True,
        )
        logging.info(f"started container: {container!r}")

        return container

    def run(self, files: Iterable[str]) -> JsonR:
        targets = [str(PurePath(p).relative_to(self.base_path)) for p in files]
        command = [
            "--config=https://r2c.dev/default-r2c-checks",
            "--json",
            "--skip-pattern-validation",
            *targets,
        ]

        output_raw = (
            self.exec_remotely(command, targets)
            if self.use_remote_docker
            else self.exec_locally(command)
        )

        output_str = output_raw.decode("utf-8").strip()
        output = json.loads(output_str)
        return output.get("results", [])

    def exec_locally(self, command: Iterable[str]) -> bytes:
        """Run the sgrep command with volume mounting.
        
        This is faster, but doesn't work with remote Docker daemons.
        """
        client = get_docker_client()

        vols = {str(self.base_path): {"bind": "/home/repo", "mode": "ro"}}
        return client.containers.run(  # type: ignore
            self.DOCKER_IMAGE, auto_remove=True, volumes=vols, command=command
        )

    def exec_remotely(self, command: Iterable[str], targets: Iterable[str]) -> bytes:
        """Run the sgrep command with target file copying.
        
        This is slower, but works with remote Docker daemons.
        """
        container = self.get_or_start_daemon()

        copy_into_container(targets, container, "/home/repo")

        output_raw: bytes = container.exec_run(  # type: ignore
            ["/bin/sgrep-lint", *command], stderr=False
        ).output
        container.stop()
        return output_raw

    def matches_project(self) -> bool:
        return DOCKER_INSTALLED.value

    @property
    def parser_type(self) -> Type[Parser]:
        return SGrepParser
