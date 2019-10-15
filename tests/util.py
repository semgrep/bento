import contextlib
import subprocess
from typing import Iterator, TextIO


@contextlib.contextmanager
def mod_file(path: str) -> Iterator[TextIO]:
    """
    Opens a path for read, then reverts it.
    """
    try:
        with open(path) as file:
            yield file
    finally:
        subprocess.run(["git", "checkout", path], check=True)
