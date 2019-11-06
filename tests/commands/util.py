import contextlib
import subprocess
from pathlib import Path
from typing import Iterator, TextIO


@contextlib.contextmanager
def mod_file(path: Path) -> Iterator[TextIO]:
    """
    Opens a path for read, then reverts it.
    """
    try:
        with path.open() as file:
            yield file
    finally:
        subprocess.run(["git", "checkout", str(path)], check=True)
