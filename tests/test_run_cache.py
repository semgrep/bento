import os
import tempfile
import time
from pathlib import Path
from typing import Tuple

from _pytest.monkeypatch import MonkeyPatch
from bento.base_context import BaseContext
from bento.run_cache import RunCache

TOOL_ID = "tool_name_here"
TOOL_OUTPUT = "this is tool output"
THIS_PATH = os.path.dirname(__file__)


def __ensure_ubuntu_mtime_change() -> None:
    """
    On Ubuntu, file mtimes are not updated if a small enough time has passed.

    To ensure mtime change, sleep at least 10 ms.
    """
    time.sleep(1e-2)


def __cache(cache_path: Path, run_path: Path) -> RunCache:
    context = BaseContext(base_path=run_path)
    ignore = context.file_ignores
    return RunCache(ignore, cache_path)


def __hash(tmp_path: Path) -> str:
    with tempfile.TemporaryDirectory() as cache_dir:
        return __cache(cache_path=Path(cache_dir), run_path=tmp_path)._modified_hash()


def __setup_test_dir(
    tmp_path: Path, subdir_name: str = "subdir", touch_file: bool = True
) -> Tuple[str, Path]:
    subdir = tmp_path / subdir_name
    subdir.mkdir()
    file = subdir / "hello.txt"
    if touch_file:
        file.touch()
    hsh = __hash(tmp_path)
    return hsh, file


def test_modified_hash_no_changes(tmp_path: Path) -> None:
    """modified_hash should not change if no files change"""

    hsh, _ = __setup_test_dir(tmp_path)
    __ensure_ubuntu_mtime_change()

    assert hsh == __hash(tmp_path)


def test_modified_hash_new_file_subdir(tmp_path: Path) -> None:
    """modified_hash should change if a new file in subdir is added"""
    hsh, file = __setup_test_dir(tmp_path, touch_file=False)

    file.touch()

    assert hsh != __hash(tmp_path)


def test_modified_hash_touch(tmp_path: Path) -> None:
    """modified_hash should change if a file is modified"""

    hsh, file = __setup_test_dir(tmp_path)
    __ensure_ubuntu_mtime_change()
    file.touch()

    assert hsh != __hash(tmp_path)


def test_modified_hash_remove(tmp_path: Path) -> None:
    """modified_hash should change if a file is removed"""

    hsh, file = __setup_test_dir(tmp_path)
    file.unlink()

    assert hsh != __hash(tmp_path)


def test_modified_hash_ignore(tmp_path: Path) -> None:
    """modifed_hash should ignore changes in exclude dirs"""
    hsh, file = __setup_test_dir(tmp_path, subdir_name=".bento", touch_file=False)

    file.touch()

    assert hsh == __hash(tmp_path)


def test_get(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    _, file = __setup_test_dir(tmp_path)

    paths = [str(tmp_path)]

    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir)

        # Check cache is retrievable
        cache = __cache(cache_path=cache_path, run_path=tmp_path)
        assert cache.get(TOOL_ID, paths) is None
        cache.put(TOOL_ID, paths, TOOL_OUTPUT)

        cache = __cache(cache_path=cache_path, run_path=tmp_path)
        assert cache.get(TOOL_ID, paths) == TOOL_OUTPUT

        # Check that modifying file invalidates cache
        __ensure_ubuntu_mtime_change()
        file.touch()

        cache = __cache(cache_path=cache_path, run_path=tmp_path)
        assert cache.get(TOOL_ID, paths) is None
