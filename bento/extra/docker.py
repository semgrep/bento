import logging
import shutil
import tarfile
from io import BytesIO
from typing import TYPE_CHECKING, Iterable

from bento.error import DockerFailureException
from bento.util import Memo

DOCKER_INSTALLED = Memo[bool](lambda: shutil.which("docker") is not None)

if TYPE_CHECKING:
    import docker.client
    from docker.models.containers import Container


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
        raise DockerFailureException()


def copy_into_container(
    paths: Iterable[str], container: "Container", destination_path: str
) -> None:
    """Copy local ``paths`` to ``destination_path`` within ``container``.

    The ``container`` is assumed to be running.
    If ``destination_path`` does not exist, it will be created.
    """
    tar_buffer = BytesIO()
    with tarfile.open(mode="w", fileobj=tar_buffer) as archive:
        for path in paths:
            archive.add(path)
    tar_buffer.seek(0)
    tar_bytes = tar_buffer.read()

    container.exec_run(["mkdir", "-p", destination_path])
    logging.info(f"sending {len(tar_bytes)} bytes to {container}")
    container.put_archive("/home/repo/", tar_bytes)
