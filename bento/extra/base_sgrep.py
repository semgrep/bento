import json
import logging
import os
import re
import subprocess
import uuid
from abc import abstractmethod
from pathlib import Path, PurePath
from typing import (
    TYPE_CHECKING,
    Any,
    Iterable,
    List,
    Mapping,
    Optional,
    Pattern,
    Tuple,
    cast,
)

from bento.extra.docker import DOCKER_INSTALLED, copy_into_container, get_docker_client
from bento.parser import Parser
from bento.tool import JsonR, JsonTool
from bento.util import fetch_line_in_file
from bento.violation import Violation

if TYPE_CHECKING:
    from docker.models.containers import Container


class BaseSgrepParser(Parser[JsonR]):
    @classmethod
    @abstractmethod
    def tool_id(cls) -> str:
        pass

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
            ).rstrip()
            violation = Violation(
                tool_id=self.tool_id(),
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


class BaseSgrepTool(JsonTool):
    DOCKER_IMAGE = "returntocorp/sgrep:0.4.8"
    FILE_NAME_FILTER = re.compile(r".*")
    UUID = str(uuid.uuid4())[:8]
    CONTAINER_LIVE_TIME = 600  # Number of seconds to keep container running

    @abstractmethod
    def get_config_str(self) -> str:
        """
        Returns the configuration argument to pass to sgrep
        """
        pass

    def get_config_path(self) -> Optional[Path]:
        """
        Returns the path to the sgrep configuration file _if it is a path_.
        Returns None otherwise.
        """
        return None

    @property
    def file_name_filter(self) -> Pattern:
        return self.FILE_NAME_FILTER

    @property
    def project_name(self) -> str:
        return "Python/JS"

    @classmethod
    def tool_desc(cls) -> str:
        return "Runs checks from r2c's check registry (experimental; requires Docker)"

    @property
    def use_remote_docker(self) -> bool:
        """Return whether the Docker daemon is remote.

        We need to know because volume mounting doesn't work with remote daemons.
        """
        return os.getenv("R2C_USE_REMOTE_DOCKER", "0") == "1"

    def matches_project(self) -> bool:
        return DOCKER_INSTALLED.value

    @property
    def container_name(self) -> str:
        """
        The name of the docker container used to run sgrep

        This is used to separate the docker instances used by each instance of Bento and
        each instance of this class within Bento.
        """
        # UUID separates instances of Bento
        # Tool ID separates instances of the BaseSgrep tool
        return f"bento-sgrep-daemon-{self.UUID}-{self.tool_id()}"

    @property
    def local_volume_mapping(self) -> Mapping[str, Any]:
        """The volumes to bind when Docker is running locally"""
        return {str(self.base_path): {"bind": "/home/repo", "mode": "ro"}}

    def setup(self) -> None:
        self.prepull_image()
        if self.use_remote_docker:
            self.get_or_start_daemon()

    def prepull_image(self) -> None:
        """
        Pulls the sgrep docker image from Docker hub
        """
        client = get_docker_client()

        if not any(i for i in client.images.list() if self.DOCKER_IMAGE in i.tags):
            client.images.pull(self.DOCKER_IMAGE)
            logging.info(f"Pre-pulled {self.tool_id()} image")

    def get_or_start_daemon(self) -> "Container":
        """
        Returns the Docker container used to run sgrep
        """
        # When this tool runs more than one time within an invocation of Bento,
        # the docker container will be reused (assuming the second run is within
        # CONTAINER_LIVE_TIME seconds)

        client = get_docker_client()

        our_containers = client.containers.list(
            filters={"name": self.container_name, "status": "running"}
        )
        if our_containers:
            logging.info(f"using existing {self.tool_id()} container")
            return our_containers[0]

        vols = {} if self.use_remote_docker else self.local_volume_mapping

        logging.info(f"starting new {self.tool_id()} container")
        container: "Container" = client.containers.run(  # type: ignore
            self.DOCKER_IMAGE,
            entrypoint=["sleep"],
            command=[str(self.CONTAINER_LIVE_TIME)],
            auto_remove=True,
            name=self.container_name,
            volumes=vols,
            detach=True,
        )
        logging.info(f"started container: {container!r}")

        return container

    def setup_remote_docker(
        self, config_str: str, container: "Container", expanded: Mapping[Path, str]
    ) -> None:
        copy_into_container(expanded, container, PurePath("/home/repo"))
        config_path = self.get_config_path()
        if config_path is not None:
            copy_into_container(
                {config_path: config_str}, container, PurePath("/home/repo")
            )

    def run(self, files: Iterable[str]) -> JsonR:
        targets: Iterable[Path] = [Path(p) for p in files]
        config_str = self.get_config_str()
        command = [
            "/bin/sgrep-lint",
            "--config",
            config_str,
            "--json",
            "--skip-pattern-validation",
        ]

        output_str = self.exec_sgrep(
            command, config_str, self.use_remote_docker, targets
        )

        output = json.loads(output_str)
        return output.get("results", [])

    def exec_sgrep(
        self,
        command: List[str],
        config_str: str,
        is_remote: bool,
        targets: Iterable[Path],
    ) -> str:
        """ Run the sgrep command """
        container = self.get_or_start_daemon()
        expanded = {t: str(t.relative_to(self.base_path)) for t in targets}

        if is_remote:
            self.setup_remote_docker(config_str, container, expanded)

        paths = list(expanded.values())

        exit_code, output_raw = cast(
            Tuple[int, bytes], container.exec_run(command + paths, workdir="/home/repo")
        )
        output = output_raw.decode("utf-8").split("\n")

        logging.info(
            f"{self.tool_id()}: Returned code {exit_code} with output[:4000]:\n{output[:4000]}"
        )

        stderr = "\n".join(output[0:-3])
        stdout = output[-2]  # stdout is always last full line of output
        if exit_code > 0:
            raise subprocess.CalledProcessError(
                cmd=command, returncode=exit_code, stderr=stderr, output=stdout
            )
        return stdout
