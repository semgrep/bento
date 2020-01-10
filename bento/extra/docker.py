import logging
import shutil
from typing import TYPE_CHECKING

from bento.util import Memo

DOCKER_INSTALLED = Memo[bool](lambda: shutil.which("docker") is not None)

if TYPE_CHECKING:
    import docker.client  # type: ignore


def get_docker_client() -> "docker.client.DockerClient":
    """Checks that docker client is reachable"""
    # import inside def for performance
    import docker

    try:
        client = docker.from_env()
        client.info()
        return client
    except Exception as e:
        logging.debug(e)
        raise Exception(
            "Failed to run docker. Please confirm docker is installed and its daemon is running in user mode."
        )
